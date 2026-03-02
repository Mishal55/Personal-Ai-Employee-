#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { loadConfig } from '../shared/src/config.js';
import PendingApprovalGenerator from '../shared/src/pending-approval.js';
import { generateVariations, validateContent, estimateEngagement } from '../shared/src/content-formatter.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load configuration
const config = loadConfig();

// Initialize pending approval generator
const approvalGenerator = new PendingApprovalGenerator(config.pendingApprovalDir);

// Initialize MCP Server
const server = new Server(
  {
    name: 'social-media-orchestrator',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Store for draft posts (in production, use a database)
 */
const draftPosts = new Map();

/**
 * Create a cross-platform post campaign
 */
async function createCrossPlatformCampaign(campaignData) {
  const {
    baseContent,
    platforms = ['facebook', 'instagram', 'twitter'],
    campaignName,
    scheduledTime
  } = campaignData;

  // Generate platform-specific variations
  const variations = generateVariations(baseContent, platforms);
  
  const posts = [];
  const approvalFiles = [];

  // Create draft for each platform
  for (const platform of platforms) {
    const variation = variations[platform];
    const validation = validateContent(variation, platform);
    
    if (!validation.valid) {
      return {
        success: false,
        error: `Validation failed for ${platform}: ${validation.errors.join(', ')}`
      };
    }

    const draft = {
      id: `draft_${platform}_${Date.now()}`,
      platform,
      content: variation,
      campaignName,
      scheduledTime,
      createdAt: new Date().toISOString(),
      status: 'draft',
      validation
    };

    draftPosts.set(draft.id, draft);
    posts.push({
      platform,
      draftId: draft.id,
      preview: variation.message || variation.caption || variation.text || '',
      characterCount: (variation.message || variation.caption || variation.text || '').length,
      engagementScore: estimateEngagement(variation, platform)
    });
  }

  // Generate cross-platform summary
  const summaryResult = await approvalGenerator.generateCrossPlatformSummary(
    posts.map(p => ({
      platform: p.platform,
      type: 'post_draft',
      preview: p.preview,
      filename: `${p.platform.toUpperCase()}_POST_${p.draftId}.md`
    })),
    { campaign: campaignName }
  );

  approvalFiles.push(summaryResult);

  return {
    success: true,
    campaignId: `campaign_${Date.now()}`,
    campaignName,
    posts,
    approvalFiles: approvalFiles.map(f => f.filepath),
    message: `Created ${posts.length} draft posts across ${platforms.length} platforms`
  };
}

/**
 * Schedule posts for publishing
 */
async function schedulePosts(scheduleData) {
  const { draftIds, schedule } = scheduleData;

  const scheduled = [];
  
  for (const draftId of draftIds) {
    const draft = draftPosts.get(draftId);
    if (!draft) {
      scheduled.push({ draftId, success: false, error: 'Draft not found' });
      continue;
    }

    draft.scheduledTime = schedule;
    draft.status = 'scheduled';
    scheduled.push({ draftId, success: true, scheduledTime: schedule });
  }

  return {
    success: true,
    scheduled,
    message: `Scheduled ${scheduled.filter(s => s.success).length} posts`
  };
}

/**
 * Get all draft posts
 */
function getAllDrafts(filter = {}) {
  const drafts = Array.from(draftPosts.values());
  
  if (filter.platform) {
    return drafts.filter(d => d.platform === filter.platform);
  }
  if (filter.status) {
    return drafts.filter(d => d.status === filter.status);
  }
  if (filter.campaignName) {
    return drafts.filter(d => d.campaignName === filter.campaignName);
  }
  
  return drafts;
}

/**
 * Delete a draft post
 */
function deleteDraft(draftId) {
  const deleted = draftPosts.delete(draftId);
  return {
    success: deleted,
    draftId,
    message: deleted ? 'Draft deleted' : 'Draft not found'
  };
}

/**
 * Generate content calendar
 */
async function generateContentCalendar(weekStart, posts) {
  const formattedPosts = posts.map(p => ({
    platform: p.platform,
    type: p.type || 'post',
    preview: p.content?.message || p.content?.caption || p.content?.text || '',
    scheduledDate: p.scheduledTime?.split('T')[0] || new Date().toISOString().split('T')[0],
    filename: `${p.platform.toUpperCase()}_${p.id}.md`
  }));

  const result = await approvalGenerator.generateContentCalendar(
    formattedPosts,
    weekStart
  );

  return {
    success: true,
    calendarFile: result.filepath,
    postCount: posts.length
  };
}

/**
 * Analyze cross-platform performance potential
 */
function analyzeCrossPlatform(content) {
  const platforms = ['facebook', 'instagram', 'twitter'];
  const analysis = {};

  for (const platform of platforms) {
    const variation = generateVariations(content, [platform])[platform];
    analysis[platform] = {
      engagementScore: estimateEngagement(variation, platform),
      validation: validateContent(variation, platform),
      optimalLength: platform === 'twitter' ? '100-280 chars' : 
                     platform === 'instagram' ? '150-500 chars + hashtags' :
                     '50-200 chars'
    };
  }

  // Find best performing platform
  const bestPlatform = platforms.reduce((best, current) => {
    return analysis[current].engagementScore > analysis[best].engagementScore 
      ? current 
      : best;
  });

  return {
    analysis,
    bestPlatform,
    recommendations: [
      `Best engagement potential on ${bestPlatform}`,
      analysis.twitter.engagementScore < 50 ? 'Consider adding media to Twitter posts' : '',
      analysis.instagram.engagementScore < 50 ? 'Add more hashtags for Instagram discoverability' : '',
      analysis.facebook.engagementScore < 50 ? 'Include a call-to-action for Facebook' : ''
    ].filter(Boolean)
  };
}

// Tool definitions
const TOOLS = [
  {
    name: 'social_create_cross_platform_campaign',
    description: 'Create a coordinated post campaign across Facebook, Instagram, and Twitter/X. Generates approval files for each platform.',
    inputSchema: {
      type: 'object',
      properties: {
        baseContent: {
          type: 'object',
          description: 'Base content for the campaign',
          properties: {
            message: { type: 'string', description: 'Main message/content' },
            link: { type: 'string', description: 'URL to share' },
            mediaUrl: { type: 'string', description: 'Media URL' },
            hashtags: { type: 'array', items: { type: 'string' } }
          }
        },
        platforms: {
          type: 'array',
          description: 'Platforms to post to',
          items: { 
            type: 'string', 
            enum: ['facebook', 'instagram', 'twitter'] 
          },
          default: ['facebook', 'instagram', 'twitter']
        },
        campaignName: {
          type: 'string',
          description: 'Campaign name for tracking'
        },
        scheduledTime: {
          type: 'string',
          description: 'Schedule publish time (ISO 8601)'
        },
        generateApprovalFiles: {
          type: 'boolean',
          description: 'Generate markdown approval files',
          default: true
        }
      },
      required: ['baseContent']
    }
  },
  {
    name: 'social_schedule_posts',
    description: 'Schedule draft posts for publishing',
    inputSchema: {
      type: 'object',
      properties: {
        draftIds: {
          type: 'array',
          description: 'IDs of drafts to schedule',
          items: { type: 'string' }
        },
        schedule: {
          type: 'string',
          description: 'Schedule time (ISO 8601)'
        }
      },
      required: ['draftIds', 'schedule']
    }
  },
  {
    name: 'social_get_all_drafts',
    description: 'Get all draft posts with optional filtering',
    inputSchema: {
      type: 'object',
      properties: {
        platform: {
          type: 'string',
          enum: ['facebook', 'instagram', 'twitter'],
          description: 'Filter by platform'
        },
        status: {
          type: 'string',
          enum: ['draft', 'scheduled', 'published'],
          description: 'Filter by status'
        },
        campaignName: {
          type: 'string',
          description: 'Filter by campaign name'
        }
      }
    }
  },
  {
    name: 'social_delete_draft',
    description: 'Delete a draft post',
    inputSchema: {
      type: 'object',
      properties: {
        draftId: {
          type: 'string',
          description: 'ID of draft to delete'
        }
      },
      required: ['draftId']
    }
  },
  {
    name: 'social_generate_content_calendar',
    description: 'Generate a content calendar for the week',
    inputSchema: {
      type: 'object',
      properties: {
        weekStart: {
          type: 'string',
          description: 'Week start date (YYYY-MM-DD)'
        },
        posts: {
          type: 'array',
          description: 'Posts to include in calendar',
          items: {
            type: 'object',
            properties: {
              platform: { type: 'string' },
              content: { type: 'object' },
              scheduledTime: { type: 'string' }
            }
          }
        }
      },
      required: ['weekStart', 'posts']
    }
  },
  {
    name: 'social_analyze_cross_platform',
    description: 'Analyze content performance potential across all platforms',
    inputSchema: {
      type: 'object',
      properties: {
        message: {
          type: 'string',
          description: 'Content to analyze'
        },
        link: {
          type: 'string',
          description: 'URL to include'
        },
        hasMedia: {
          type: 'boolean',
          description: 'Whether content includes media'
        }
      },
      required: ['message']
    }
  },
  {
    name: 'social_generate_platform_variations',
    description: 'Generate platform-specific content variations',
    inputSchema: {
      type: 'object',
      properties: {
        baseContent: {
          type: 'object',
          description: 'Base content',
          properties: {
            message: { type: 'string' },
            link: { type: 'string' },
            hashtags: { type: 'array', items: { type: 'string' } }
          }
        },
        platforms: {
          type: 'array',
          items: { type: 'string' },
          default: ['facebook', 'instagram', 'twitter']
        }
      },
      required: ['baseContent']
    }
  }
];

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'social_create_cross_platform_campaign': {
        const result = await createCrossPlatformCampaign(args);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'social_schedule_posts': {
        const result = await schedulePosts(args);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'social_get_all_drafts': {
        const drafts = getAllDrafts(args);
        return {
          content: [{ type: 'text', text: JSON.stringify({ drafts, count: drafts.length }, null, 2) }]
        };
      }

      case 'social_delete_draft': {
        const result = deleteDraft(args.draftId);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'social_generate_content_calendar': {
        const result = await generateContentCalendar(args.weekStart, args.posts);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'social_analyze_cross_platform': {
        const result = analyzeCrossPlatform(args);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'social_generate_platform_variations': {
        const variations = generateVariations(args.baseContent, args.platforms);
        return {
          content: [{ type: 'text', text: JSON.stringify({ variations }, null, 2) }]
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
    console.error('Social Media Orchestrator running on stdio');
    console.error(`Pending Approval Dir: ${config.pendingApprovalDir}`);
    console.error(`Platforms: Facebook, Instagram, Twitter/X`);
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

main();
