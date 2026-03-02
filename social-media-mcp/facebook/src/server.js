#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import http from 'http';
import https from 'https';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { loadConfig } from '../../shared/src/config.js';
import PendingApprovalGenerator from '../../shared/src/pending-approval.js';
import { validateContent, estimateEngagement } from '../../shared/src/content-formatter.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load configuration
const config = loadConfig('facebook');
const globalConfig = loadConfig();

// Initialize pending approval generator
const approvalGenerator = new PendingApprovalGenerator(globalConfig.pendingApprovalDir);

// Initialize MCP Server
const server = new Server(
  {
    name: 'facebook-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Make a Facebook Graph API request
 */
async function graphApiRequest(endpoint, method = 'GET', params = {}) {
  const baseUrl = `https://graph.facebook.com/${config.apiVersion}`;
  const url = new URL(`${baseUrl}/${endpoint}`);
  
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
            reject(new Error(result.error.message || 'Facebook API Error'));
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
 * Create a draft post on Facebook
 */
async function createDraftPost(postData) {
  const {
    message,
    link,
    picture,
    place,
    tags,
    scheduledTime,
    published = false
  } = postData;

  const params = {
    message: message || '',
    published: published ? 'true' : 'false'
  };

  if (link) params.link = link;
  if (picture) params.picture = picture;
  if (place) params.place = place;
  if (tags && tags.length > 0) params.tags = tags.join(',');
  if (scheduledTime) params.scheduled_publish_time = Math.floor(new Date(scheduledTime).getTime() / 1000);

  const result = await graphApiRequest(`/${config.pageId}/feed`, 'POST', params);
  
  return {
    success: true,
    postId: result.id,
    message: published ? 'Post published successfully' : 'Draft post created successfully',
    published: published,
    postUrl: `https://facebook.com/${result.id}`
  };
}

/**
 * Get page information
 */
async function getPageInfo() {
  const result = await graphApiRequest(`/${config.pageId}`, 'GET', {
    fields: 'id,name,username,about,followers_count,likes,website'
  });
  return result;
}

/**
 * Get recent posts from page
 */
async function getRecentPosts(limit = 10) {
  const result = await graphApiRequest(`/${config.pageId}/posts`, 'GET', {
    fields: 'id,message,created_time,permalink_url,shares,likes.summary(true),comments.summary(true)',
    limit: limit
  });
  return result.data || [];
}

/**
 * Get page insights
 */
async function getPageInsights(metricNames = ['page_impressions', 'page_engaged_users', 'page_post_engagements']) {
  const result = await graphApiRequest(`/${config.pageId}/insights`, 'GET', {
    metric: metricNames.join(','),
    period: 'day'
  });
  return result.data || [];
}

/**
 * Search for pages
 */
async function searchPages(query, limit = 10) {
  const result = await graphApiRequest('/search', 'GET', {
    q: query,
    type: 'page',
    limit: limit
  });
  return result.data || [];
}

// Tool definitions
const TOOLS = [
  {
    name: 'facebook_create_draft_post',
    description: 'Create a draft post on Facebook. Post is saved as unpublished for review before publishing. Generates markdown file in /Pending_Approval.',
    inputSchema: {
      type: 'object',
      properties: {
        message: {
          type: 'string',
          description: 'Post message/content (max 63,206 characters)'
        },
        link: {
          type: 'string',
          description: 'URL to share'
        },
        picture: {
          type: 'string',
          description: 'URL of image to include'
        },
        place: {
          type: 'string',
          description: 'Location ID or name'
        },
        tags: {
          type: 'array',
          description: 'User IDs to tag',
          items: { type: 'string' }
        },
        scheduledTime: {
          type: 'string',
          description: 'Schedule publish time (ISO 8601)'
        },
        generateApprovalFile: {
          type: 'boolean',
          description: 'Generate markdown approval file',
          default: true
        }
      },
      required: ['message']
    }
  },
  {
    name: 'facebook_publish_post',
    description: 'Publish a draft post or create and publish a new post immediately',
    inputSchema: {
      type: 'object',
      properties: {
        message: {
          type: 'string',
          description: 'Post message/content'
        },
        link: {
          type: 'string',
          description: 'URL to share'
        },
        picture: {
          type: 'string',
          description: 'URL of image to include'
        },
        postId: {
          type: 'string',
          description: 'ID of draft post to publish'
        }
      }
    }
  },
  {
    name: 'facebook_get_page_info',
    description: 'Get information about the Facebook page',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'facebook_get_recent_posts',
    description: 'Get recent posts from the Facebook page',
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
    name: 'facebook_get_insights',
    description: 'Get page insights and analytics',
    inputSchema: {
      type: 'object',
      properties: {
        metrics: {
          type: 'array',
          description: 'Metrics to retrieve',
          items: { type: 'string' },
          default: ['page_impressions', 'page_engaged_users', 'page_post_engagements']
        }
      }
    }
  },
  {
    name: 'facebook_search_pages',
    description: 'Search for Facebook pages',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query'
        },
        limit: {
          type: 'integer',
          description: 'Number of results',
          default: 10
        }
      },
      required: ['query']
    }
  },
  {
    name: 'facebook_analyze_content',
    description: 'Analyze Facebook post content for engagement potential',
    inputSchema: {
      type: 'object',
      properties: {
        message: {
          type: 'string',
          description: 'Post message to analyze'
        },
        hasMedia: {
          type: 'boolean',
          description: 'Whether post includes media'
        },
        hasLink: {
          type: 'boolean',
          description: 'Whether post includes a link'
        }
      },
      required: ['message']
    }
  }
];

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'facebook_create_draft_post': {
        const { generateApprovalFile = true, ...postData } = args;

        // Validate content
        const validation = validateContent(postData, 'facebook');
        if (!validation.valid) {
          return {
            content: [{ type: 'text', text: JSON.stringify({ error: validation.errors }, null, 2) }],
            isError: true
          };
        }

        // Generate approval file first
        let approvalResult = null;
        if (generateApprovalFile) {
          approvalResult = await approvalGenerator.generateFacebookDraft({
            ...postData,
            targetAudience: 'Public',
            campaign: 'Social Media Campaign'
          });
          console.error(`Approval file generated: ${approvalResult.filepath}`);
        }

        // Create draft post (published=false)
        const result = await createDraftPost({
          ...postData,
          published: false
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

      case 'facebook_publish_post': {
        const result = await createDraftPost({
          ...args,
          published: true
        });

        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'facebook_get_page_info': {
        const pageInfo = await getPageInfo();
        return {
          content: [{ type: 'text', text: JSON.stringify(pageInfo, null, 2) }]
        };
      }

      case 'facebook_get_recent_posts': {
        const posts = await getRecentPosts(args.limit || 10);
        return {
          content: [{ type: 'text', text: JSON.stringify({ posts }, null, 2) }]
        };
      }

      case 'facebook_get_insights': {
        const insights = await getPageInsights(args.metrics);
        return {
          content: [{ type: 'text', text: JSON.stringify({ insights }, null, 2) }]
        };
      }

      case 'facebook_search_pages': {
        const pages = await searchPages(args.query, args.limit || 10);
        return {
          content: [{ type: 'text', text: JSON.stringify({ pages }, null, 2) }]
        };
      }

      case 'facebook_analyze_content': {
        const engagement = estimateEngagement(args, 'facebook');
        const validation = validateContent(args, 'facebook');
        
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              engagementScore: engagement,
              validation,
              recommendations: [
                engagement < 50 ? 'Consider adding media to increase engagement' : '',
                engagement < 50 && !args.hasLink ? 'Adding a relevant link may boost engagement' : '',
                validation.warnings?.length > 0 ? validation.warnings.join(', ') : ''
              ].filter(Boolean)
            }, null, 2)
          }]
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
    console.error('Facebook MCP Server running on stdio');
    console.error(`Page ID: ${config.pageId}`);
    console.error(`Pending Approval Dir: ${globalConfig.pendingApprovalDir}`);
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

main();
