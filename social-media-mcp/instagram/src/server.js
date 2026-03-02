#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import https from 'https';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { loadConfig } from '../../shared/src/config.js';
import PendingApprovalGenerator from '../../shared/src/pending-approval.js';
import { validateContent, estimateEngagement, PLATFORM_LIMITS } from '../../shared/src/content-formatter.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load configuration
const config = loadConfig('instagram');
const globalConfig = loadConfig();

// Initialize pending approval generator
const approvalGenerator = new PendingApprovalGenerator(globalConfig.pendingApprovalDir);

// Initialize MCP Server
const server = new Server(
  {
    name: 'instagram-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Make an Instagram Graph API request
 */
async function graphApiRequest(endpoint, method = 'GET', params = {}, usePostsEndpoint = false) {
  const baseUrl = `https://graph.facebook.com/${config.apiVersion}`;
  const url = new URL(`${baseUrl}/${usePostsEndpoint ? '' : ''}${endpoint}`);
  
  // Add access token to all requests
  url.searchParams.append('access_token', config.accessToken);
  
  // Add additional params
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      url.searchParams.append(key, value);
    }
  }

  return new Promise((resolve, reject) => {
    const options = {
      method: method,
      headers: {
        'Content-Type': 'application/json'
      }
    };

    const req = https.request(url.toString(), options, (res) => {
      let responseData = '';
      res.on('data', chunk => responseData += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(responseData);
          if (result.error) {
            reject(new Error(result.error.message || 'Instagram API Error'));
          } else {
            resolve(result);
          }
        } catch (e) {
          reject(new Error(`Failed to parse response: ${e.message}`));
        }
      });
    });

    req.on('error', reject);
    req.end();
  });
}

/**
 * Create a media container (draft post)
 */
async function createMediaContainer(mediaData) {
  const {
    mediaType = 'IMAGE',
    mediaUrl,
    thumbnailUrl,
    caption,
    isReel = false,
    isCarousel = false,
    children = []
  } = mediaData;

  const params = {
    image_url: mediaType === 'IMAGE' ? mediaUrl : undefined,
    video_url: mediaType === 'VIDEO' ? mediaUrl : undefined,
    media_type: isReel ? 'REELS' : mediaType,
    caption: caption || ''
  };

  if (mediaType === 'CAROUSEL') {
    params.children = JSON.stringify(children.map(c => ({ image_url: c.image_url, video_url: c.video_url })));
  }

  if (thumbnailUrl) {
    params.thumb_url = thumbnailUrl;
  }

  // Create media container
  const containerResult = await graphApiRequest(
    `/${config.instagramAccountId}/media`,
    'POST',
    params
  );

  return containerResult;
}

/**
 * Publish a media container
 */
async function publishMedia(containerId) {
  const result = await graphApiRequest(
    `/${config.instagramAccountId}/media_publish`,
    'POST',
    { creation_id: containerId }
  );

  return result;
}

/**
 * Create a draft post (container without publishing)
 */
async function createDraftPost(postData) {
  const containerResult = await createMediaContainer(postData);
  
  return {
    success: true,
    containerId: containerResult.id,
    message: 'Draft post created successfully. Use publish_media to publish.',
    status: 'draft',
    expiresIn: '24 hours (Instagram requirement)'
  };
}

/**
 * Get Instagram account info
 */
async function getAccountInfo() {
  const result = await graphApiRequest(`/${config.instagramAccountId}`, 'GET', {
    fields: 'id,username,biography,website,followers_count,follows_count,media_count,profile_picture_url'
  });
  return result;
}

/**
 * Get recent media posts
 */
async function getRecentMedia(limit = 10) {
  const result = await graphApiRequest(`/${config.instagramAccountId}/media`, 'GET', {
    fields: 'id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count',
    limit: limit
  });
  return result.data || [];
}

/**
 * Get media insights
 */
async function getMediaInsights(mediaId) {
  const result = await graphApiRequest(`/${mediaId}/insights`, 'GET', {
    metric: 'impressions,reach,engagement,saved'
  });
  return result.data || [];
}

/**
 * Get content publishing limits
 */
async function getContentPublishingLimits() {
  const result = await graphApiRequest(`/${config.instagramAccountId}/content_publishing_limit`, 'GET');
  return result;
}

/**
 * Search for hashtags
 */
async function searchHashtags(query, limit = 10) {
  // Instagram doesn't have a direct hashtag search API
  // This is a placeholder for hashtag suggestions
  const suggestions = [
    query,
    `${query}life`,
    `${query}love`,
    `${query}daily`,
    `instag${query}`,
    `${query}gram`
  ];
  
  return suggestions.slice(0, limit);
}

/**
 * Generate optimal hashtags for content
 */
function generateHashtags(content, industry = 'general') {
  const baseHashtags = {
    general: ['instagood', 'photooftheday', 'beautiful', 'happy', 'picoftheday'],
    business: ['business', 'entrepreneur', 'success', 'motivation', 'hustle'],
    food: ['foodie', 'foodporn', 'instafood', 'delicious', 'yummy'],
    travel: ['travel', 'wanderlust', 'travelgram', 'adventure', 'explore'],
    fitness: ['fitness', 'gym', 'workout', 'fit', 'health'],
    fashion: ['fashion', 'style', 'ootd', 'fashionista', 'outfit']
  };

  const industryTags = baseHashtags[industry] || baseHashtags.general;
  
  // Extract words from content for custom hashtags
  const words = content.toLowerCase()
    .replace(/[^\w\s]/g, '')
    .split(/\s+/)
    .filter(w => w.length > 3 && !['the', 'and', 'with', 'this', 'that'].includes(w))
    .slice(0, 5);

  const customTags = words.map(w => w.substring(0, 15));
  
  return [...customTags, ...industryTags].slice(0, PLATFORM_LIMITS.instagram.hashtags);
}

// Tool definitions
const TOOLS = [
  {
    name: 'instagram_create_draft_post',
    description: 'Create a draft post on Instagram. Post is saved as a media container for review before publishing. Generates markdown file in /Pending_Approval.',
    inputSchema: {
      type: 'object',
      properties: {
        caption: {
          type: 'string',
          description: 'Post caption (max 2,200 characters)'
        },
        mediaUrl: {
          type: 'string',
          description: 'URL of the image or video'
        },
        mediaType: {
          type: 'string',
          enum: ['IMAGE', 'VIDEO', 'CAROUSEL'],
          description: 'Type of media',
          default: 'IMAGE'
        },
        thumbnailUrl: {
          type: 'string',
          description: 'Thumbnail URL for videos'
        },
        location: {
          type: 'string',
          description: 'Location ID or name'
        },
        hashtags: {
          type: 'array',
          description: 'Hashtags (max 30)',
          items: { type: 'string' }
        },
        isReel: {
          type: 'boolean',
          description: 'Create as Reel instead of post',
          default: false
        },
        generateApprovalFile: {
          type: 'boolean',
          description: 'Generate markdown approval file',
          default: true
        }
      },
      required: ['mediaUrl']
    }
  },
  {
    name: 'instagram_publish_media',
    description: 'Publish a draft media container to Instagram',
    inputSchema: {
      type: 'object',
      properties: {
        containerId: {
          type: 'string',
          description: 'ID of the media container to publish'
        }
      },
      required: ['containerId']
    }
  },
  {
    name: 'instagram_create_reel',
    description: 'Create a draft Instagram Reel',
    inputSchema: {
      type: 'object',
      properties: {
        caption: {
          type: 'string',
          description: 'Reel caption'
        },
        videoUrl: {
          type: 'string',
          description: 'URL of the video'
        },
        thumbnailUrl: {
          type: 'string',
          description: 'Thumbnail URL'
        },
        hashtags: {
          type: 'array',
          description: 'Hashtags',
          items: { type: 'string' }
        },
        generateApprovalFile: {
          type: 'boolean',
          description: 'Generate markdown approval file',
          default: true
        }
      },
      required: ['videoUrl']
    }
  },
  {
    name: 'instagram_get_account_info',
    description: 'Get Instagram account information',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'instagram_get_recent_media',
    description: 'Get recent media posts from Instagram account',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'integer',
          description: 'Number of posts to retrieve',
          default: 10
        }
      }
    }
  },
  {
    name: 'instagram_get_media_insights',
    description: 'Get insights for a specific media post',
    inputSchema: {
      type: 'object',
      properties: {
        mediaId: {
          type: 'string',
          description: 'Instagram media ID'
        }
      },
      required: ['mediaId']
    }
  },
  {
    name: 'instagram_generate_hashtags',
    description: 'Generate optimal hashtags for Instagram content',
    inputSchema: {
      type: 'object',
      properties: {
        content: {
          type: 'string',
          description: 'Post content/caption'
        },
        industry: {
          type: 'string',
          description: 'Industry/category',
          enum: ['general', 'business', 'food', 'travel', 'fitness', 'fashion']
        },
        count: {
          type: 'integer',
          description: 'Number of hashtags to generate',
          default: 15
        }
      },
      required: ['content']
    }
  },
  {
    name: 'instagram_analyze_content',
    description: 'Analyze Instagram post content for engagement potential',
    inputSchema: {
      type: 'object',
      properties: {
        caption: {
          type: 'string',
          description: 'Post caption to analyze'
        },
        hasMedia: {
          type: 'boolean',
          description: 'Whether post includes media'
        },
        mediaType: {
          type: 'string',
          description: 'Type of media',
          enum: ['IMAGE', 'VIDEO', 'CAROUSEL', 'REEL']
        }
      },
      required: ['caption']
    }
  },
  {
    name: 'instagram_get_publishing_limits',
    description: 'Get content publishing limits for the account',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  }
];

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'instagram_create_draft_post': {
        const { generateApprovalFile = true, hashtags = [], ...postData } = args;

        // Validate content
        const validation = validateContent({ ...postData, hashtags }, 'instagram');
        if (!validation.valid) {
          return {
            content: [{ type: 'text', text: JSON.stringify({ error: validation.errors }, null, 2) }],
            isError: true
          };
        }

        // Generate approval file first
        let approvalResult = null;
        if (generateApprovalFile) {
          approvalResult = await approvalGenerator.generateInstagramDraft({
            ...postData,
            hashtags,
            taggedUsers: [],
            scheduledTime: null
          });
          console.error(`Approval file generated: ${approvalResult.filepath}`);
        }

        // Create draft post
        const result = await createDraftPost({
          ...postData,
          hashtags: hashtags.join(' ')
        });

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                ...result,
                approvalFile: approvalResult?.filepath,
                validation: { warnings: validation.warnings }
              }, null, 2)
            }
          ]
        };
      }

      case 'instagram_publish_media': {
        const result = await publishMedia(args.containerId);
        return {
          content: [{ type: 'text', text: JSON.stringify({
            success: true,
            publishedMediaId: result.id,
            message: 'Media published successfully'
          }, null, 2) }]
        };
      }

      case 'instagram_create_reel': {
        const { generateApprovalFile = true, hashtags = [], ...postData } = args;

        // Generate approval file first
        let approvalResult = null;
        if (generateApprovalFile) {
          approvalResult = await approvalGenerator.generateInstagramDraft({
            caption: postData.caption,
            mediaUrl: postData.videoUrl,
            mediaType: 'VIDEO',
            hashtags,
            isReel: true
          });
          console.error(`Approval file generated: ${approvalResult.filepath}`);
        }

        // Create draft reel
        const result = await createDraftPost({
          mediaType: 'VIDEO',
          mediaUrl: postData.videoUrl,
          thumbnailUrl: postData.thumbnailUrl,
          caption: postData.caption,
          isReel: true,
          hashtags: hashtags.join(' ')
        });

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                ...result,
                approvalFile: approvalResult?.filepath,
                type: 'reel_draft'
              }, null, 2)
            }
          ]
        };
      }

      case 'instagram_get_account_info': {
        const info = await getAccountInfo();
        return {
          content: [{ type: 'text', text: JSON.stringify(info, null, 2) }]
        };
      }

      case 'instagram_get_recent_media': {
        const media = await getRecentMedia(args.limit || 10);
        return {
          content: [{ type: 'text', text: JSON.stringify({ media }, null, 2) }]
        };
      }

      case 'instagram_get_media_insights': {
        const insights = await getMediaInsights(args.mediaId);
        return {
          content: [{ type: 'text', text: JSON.stringify({ insights }, null, 2) }]
        };
      }

      case 'instagram_generate_hashtags': {
        const hashtags = generateHashtags(args.content, args.industry);
        const limited = hashtags.slice(0, args.count || 15);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              hashtags: limited,
              formatted: limited.map(h => `#${h}`).join(' '),
              count: limited.length
            }, null, 2)
          }]
        };
      }

      case 'instagram_analyze_content': {
        const engagement = estimateEngagement({
          message: args.caption,
          mediaUrls: args.hasMedia ? [args.mediaType || 'IMAGE'] : []
        }, 'instagram');
        const validation = validateContent({ caption: args.caption }, 'instagram');
        
        const mediaBonus = {
          'REEL': 25,
          'CAROUSEL': 15,
          'VIDEO': 15,
          'IMAGE': 10
        };
        
        const adjustedEngagement = Math.min(100, engagement + (mediaBonus[args.mediaType] || 0));

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              engagementScore: Math.round(adjustedEngagement),
              validation,
              recommendations: [
                args.mediaType !== 'REEL' ? 'Consider creating a Reel for higher engagement' : '',
                engagement < 50 ? 'Add more relevant hashtags to increase discoverability' : '',
                validation.warnings?.length > 0 ? validation.warnings.join(', ') : ''
              ].filter(Boolean)
            }, null, 2)
          }]
        };
      }

      case 'instagram_get_publishing_limits': {
        const limits = await getContentPublishingLimits();
        return {
          content: [{ type: 'text', text: JSON.stringify(limits, null, 2) }]
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ error: error.message }, null, 2)
        }
      ],
      isError: true
    };
  }
});

// Handle tool list request
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: TOOLS };
});

// Start the server
async function main() {
  try {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('Instagram MCP Server running on stdio');
    console.error(`Account ID: ${config.instagramAccountId}`);
    console.error(`Pending Approval Dir: ${globalConfig.pendingApprovalDir}`);
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

main();
