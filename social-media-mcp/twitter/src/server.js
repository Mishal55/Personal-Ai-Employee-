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
import { validateContent, estimateEngagement, PLATFORM_LIMITS, truncate } from '../../shared/src/content-formatter.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load configuration
const config = loadConfig('twitter');
const globalConfig = loadConfig();

// Initialize pending approval generator
const approvalGenerator = new PendingApprovalGenerator(globalConfig.pendingApprovalDir);

// Initialize MCP Server
const server = new Server(
  {
    name: 'twitter-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Generate OAuth 1.0a signature header
 * Simplified version - in production, use a proper OAuth library
 */
function generateAuthHeader(method, url, params) {
  // This is a placeholder - proper OAuth 1.0a implementation required for production
  // Twitter API v2 uses OAuth 2.0 Bearer token for most endpoints
  return `Bearer ${config.bearerToken}`;
}

/**
 * Make a Twitter API v2 request
 */
async function twitterApiRequest(endpoint, method = 'GET', body = null) {
  const baseUrl = 'https://api.twitter.com/2';
  const url = `${baseUrl}${endpoint}`;

  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    
    const options = {
      method: method,
      headers: {
        'Authorization': `Bearer ${config.bearerToken}`,
        'Content-Type': 'application/json',
        'User-Agent': 'TwitterMCPServer/1.0'
      }
    };

    const req = https.request(urlObj.toString(), options, (res) => {
      let responseData = '';
      res.on('data', chunk => responseData += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(responseData);
          if (result.errors) {
            reject(new Error(result.errors[0]?.message || 'Twitter API Error'));
          } else {
            resolve(result);
          }
        } catch (e) {
          reject(new Error(`Failed to parse response: ${e.message}`));
        }
      });
    });

    req.on('error', reject);
    
    if (body && (method === 'POST' || method === 'PUT')) {
      req.write(JSON.stringify(body));
    }
    
    req.end();
  });
}

/**
 * Create a draft tweet (stored locally, Twitter doesn't have native drafts API)
 */
async function createDraftTweet(tweetData) {
  const {
    text,
    mediaUrls = [],
    poll,
    replySettings = 'everyone',
    scheduledTime
  } = tweetData;

  // Validate tweet length
  if (text.length > PLATFORM_LIMITS.twitter.tweet) {
    throw new Error(`Tweet exceeds ${PLATFORM_LIMITS.twitter.tweet} character limit`);
  }

  // Create draft object (stored locally since Twitter doesn't have drafts API)
  const draft = {
    text,
    mediaUrls,
    poll,
    replySettings,
    scheduledTime,
    createdAt: new Date().toISOString(),
    status: 'draft'
  };

  return {
    success: true,
    draft,
    message: 'Draft tweet created. Note: Twitter does not have a native drafts API, so drafts are stored locally.',
    characterCount: text.length,
    remainingCharacters: PLATFORM_LIMITS.twitter.tweet - text.length
  };
}

/**
 * Create a tweet thread (draft)
 */
async function createDraftThread(tweets) {
  if (!Array.isArray(tweets) || tweets.length === 0) {
    throw new Error('Thread must contain at least one tweet');
  }

  // Validate each tweet
  const validatedTweets = tweets.map((tweet, index) => {
    if (tweet.text.length > PLATFORM_LIMITS.twitter.tweet) {
      throw new Error(`Tweet ${index + 1} exceeds character limit`);
    }
    return {
      ...tweet,
      position: index + 1
    };
  });

  const totalLength = tweets.reduce((sum, t) => sum + t.text.length, 0);

  return {
    success: true,
    thread: validatedTweets,
    tweetCount: tweets.length,
    totalCharacters: totalLength,
    message: `Draft thread created with ${tweets.length} tweets`,
    status: 'draft'
  };
}

/**
 * Publish a tweet to Twitter
 */
async function publishTweet(tweetData) {
  const {
    text,
    mediaUrls = [],
    poll,
    replySettings = 'everyone'
  } = tweetData;

  const body = {
    text: text,
    reply: {
      reply_settings: replySettings
    }
  };

  // Note: Media upload requires separate endpoint and OAuth 1.0a
  // This is a simplified implementation

  const result = await twitterApiRequest('/tweets', 'POST', body);
  
  return {
    success: true,
    tweetId: result.data.id,
    tweetUrl: `https://twitter.com/user/status/${result.data.id}`,
    published: true
  };
}

/**
 * Get user's recent tweets
 */
async function getUserTweets(userId, limit = 10) {
  const result = await twitterApiRequest(
    `/users/${userId}/tweets`,
    'GET'
  );
  
  return result.data || [];
}

/**
 * Get tweet by ID
 */
async function getTweetById(tweetId) {
  const result = await twitterApiRequest(
    `/tweets/${tweetId}`,
    'GET',
    {
      'tweet.fields': 'created_at,public_metrics,context_annotations'
    }
  );
  
  return result.data;
}

/**
 * Get user's followers count
 */
async function getUserFollowers(userId) {
  const result = await twitterApiRequest(
    `/users/${userId}`,
    'GET',
    {
      'user.fields': 'public_metrics,description,verified'
    }
  );
  
  return result.data;
}

/**
 * Search tweets
 */
async function searchTweets(query, limit = 10) {
  const result = await twitterApiRequest(
    `/tweets/search/recent`,
    'GET',
    {
      query: query,
      max_results: Math.min(limit, 100)
    }
  );
  
  return result.data || [];
}

/**
 * Generate trending topics suggestions
 */
function generateTrendingSuggestions(content) {
  const words = content.toLowerCase()
    .replace(/[^\w\s]/g, '')
    .split(/\s+/)
    .filter(w => w.length > 3);
  
  const uniqueWords = [...new Set(words)];
  
  return uniqueWords.slice(0, 5).map(w => `#${w.charAt(0).toUpperCase()}${w.slice(1)}`);
}

/**
 * Split long content into thread
 */
function splitIntoThread(content, maxTweetLength = 280) {
  const tweets = [];
  const paragraphs = content.split(/\n\n+/);
  
  let currentTweet = '';
  
  for (const paragraph of paragraphs) {
    if (paragraph.length > maxTweetLength) {
      // Split long paragraph
      const sentences = paragraph.split(/(?<=[.!?])\s+/);
      
      for (const sentence of sentences) {
        if ((currentTweet + ' ' + sentence).trim().length <= maxTweetLength) {
          currentTweet += (currentTweet ? ' ' : '') + sentence;
        } else {
          if (currentTweet) tweets.push(currentTweet);
          currentTweet = sentence;
        }
      }
    } else if ((currentTweet + '\n\n' + paragraph).trim().length <= maxTweetLength) {
      currentTweet += (currentTweet ? '\n\n' : '') + paragraph;
    } else {
      if (currentTweet) tweets.push(currentTweet);
      currentTweet = paragraph;
    }
  }
  
  if (currentTweet) tweets.push(currentTweet);
  
  return tweets.map((text, index) => ({
    text,
    position: index + 1
  }));
}

// Tool definitions
const TOOLS = [
  {
    name: 'twitter_create_draft_tweet',
    description: 'Create a draft tweet on Twitter/X. Draft is stored locally (Twitter has no native drafts API). Generates markdown file in /Pending_Approval.',
    inputSchema: {
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: 'Tweet text (max 280 characters)'
        },
        mediaUrls: {
          type: 'array',
          description: 'URLs of media to attach',
          items: { type: 'string' }
        },
        poll: {
          type: 'object',
          description: 'Poll configuration',
          properties: {
            question: { type: 'string' },
            options: { 
              type: 'array', 
              items: { type: 'string' },
              maxItems: 4
            },
            durationMinutes: { type: 'integer', default: 1440 }
          }
        },
        replySettings: {
          type: 'string',
          enum: ['everyone', 'mentionedUsers', 'following'],
          description: 'Who can reply',
          default: 'everyone'
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
      required: ['text']
    }
  },
  {
    name: 'twitter_create_draft_thread',
    description: 'Create a draft tweet thread on Twitter/X. Generates markdown file in /Pending_Approval.',
    inputSchema: {
      type: 'object',
      properties: {
        tweets: {
          type: 'array',
          description: 'Array of tweet objects',
          items: {
            type: 'object',
            properties: {
              text: { type: 'string' },
              mediaUrls: { type: 'array', items: { type: 'string' } }
            },
            required: ['text']
          }
        },
        generateApprovalFile: {
          type: 'boolean',
          description: 'Generate markdown approval file',
          default: true
        }
      },
      required: ['tweets']
    }
  },
  {
    name: 'twitter_split_into_thread',
    description: 'Split long content into a tweet thread',
    inputSchema: {
      type: 'object',
      properties: {
        content: {
          type: 'string',
          description: 'Long content to split'
        },
        maxTweetLength: {
          type: 'integer',
          description: 'Max characters per tweet',
          default: 280
        }
      },
      required: ['content']
    }
  },
  {
    name: 'twitter_publish_tweet',
    description: 'Publish a tweet to Twitter/X',
    inputSchema: {
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: 'Tweet text'
        },
        mediaUrls: {
          type: 'array',
          description: 'URLs of media to attach',
          items: { type: 'string' }
        },
        replySettings: {
          type: 'string',
          enum: ['everyone', 'mentionedUsers', 'following'],
          description: 'Who can reply',
          default: 'everyone'
        }
      },
      required: ['text']
    }
  },
  {
    name: 'twitter_get_user_info',
    description: 'Get Twitter user information',
    inputSchema: {
      type: 'object',
      properties: {
        userId: {
          type: 'string',
          description: 'Twitter user ID or username'
        }
      },
      required: ['userId']
    }
  },
  {
    name: 'twitter_get_recent_tweets',
    description: 'Get recent tweets from a user',
    inputSchema: {
      type: 'object',
      properties: {
        userId: {
          type: 'string',
          description: 'Twitter user ID'
        },
        limit: {
          type: 'integer',
          description: 'Number of tweets',
          default: 10
        }
      },
      required: ['userId']
    }
  },
  {
    name: 'twitter_search_tweets',
    description: 'Search for tweets',
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
    name: 'twitter_generate_hashtags',
    description: 'Generate hashtag suggestions for tweet content',
    inputSchema: {
      type: 'object',
      properties: {
        content: {
          type: 'string',
          description: 'Tweet content'
        },
        count: {
          type: 'integer',
          description: 'Number of hashtags',
          default: 5
        }
      },
      required: ['content']
    }
  },
  {
    name: 'twitter_analyze_content',
    description: 'Analyze tweet content for engagement potential',
    inputSchema: {
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: 'Tweet text to analyze'
        },
        hasMedia: {
          type: 'boolean',
          description: 'Whether tweet includes media'
        },
        hasPoll: {
          type: 'boolean',
          description: 'Whether tweet includes a poll'
        }
      },
      required: ['text']
    }
  }
];

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'twitter_create_draft_tweet': {
        const { generateApprovalFile = true, mediaUrls = [], ...tweetData } = args;

        // Validate content
        const validation = validateContent({ ...tweetData, hashtags: [] }, 'twitter');
        if (!validation.valid) {
          return {
            content: [{ type: 'text', text: JSON.stringify({ error: validation.errors }, null, 2) }],
            isError: true
          };
        }

        // Generate approval file first
        let approvalResult = null;
        if (generateApprovalFile) {
          approvalResult = await approvalGenerator.generateTwitterDraft({
            ...tweetData,
            mediaUrls,
            isThread: false
          });
          console.error(`Approval file generated: ${approvalResult.filepath}`);
        }

        // Create draft tweet
        const result = await createDraftTweet({
          ...tweetData,
          mediaUrls
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

      case 'twitter_create_draft_thread': {
        const { generateApprovalFile = true, tweets = [] } = args;

        // Generate approval file first
        let approvalResult = null;
        if (generateApprovalFile) {
          const preview = tweets.map(t => t.text).join('\n\n');
          approvalResult = await approvalGenerator.generateTwitterDraft({
            text: preview.substring(0, 500),
            isThread: true,
            threadTweets: tweets.length
          });
          console.error(`Approval file generated: ${approvalResult.filepath}`);
        }

        // Create draft thread
        const result = await createDraftThread(tweets);

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                ...result,
                approvalFile: approvalResult?.filepath
              }, null, 2)
            }
          ]
        };
      }

      case 'twitter_split_into_thread': {
        const thread = splitIntoThread(args.content, args.maxTweetLength || 280);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              thread,
              tweetCount: thread.length,
              totalCharacters: args.content.length
            }, null, 2)
          }]
        };
      }

      case 'twitter_publish_tweet': {
        const result = await publishTweet(args);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'twitter_get_user_info': {
        const userInfo = await getUserFollowers(args.userId);
        return {
          content: [{ type: 'text', text: JSON.stringify(userInfo, null, 2) }]
        };
      }

      case 'twitter_get_recent_tweets': {
        const tweets = await getUserTweets(args.userId, args.limit || 10);
        return {
          content: [{ type: 'text', text: JSON.stringify({ tweets }, null, 2) }]
        };
      }

      case 'twitter_search_tweets': {
        const tweets = await searchTweets(args.query, args.limit || 10);
        return {
          content: [{ type: 'text', text: JSON.stringify({ tweets }, null, 2) }]
        };
      }

      case 'twitter_generate_hashtags': {
        const hashtags = generateTrendingSuggestions(args.content);
        const limited = hashtags.slice(0, args.count || 5);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              hashtags: limited,
              formatted: limited.join(' '),
              count: limited.length
            }, null, 2)
          }]
        };
      }

      case 'twitter_analyze_content': {
        const engagement = estimateEngagement({
          text: args.text,
          mediaUrls: args.hasMedia ? ['media'] : [],
          poll: args.hasPoll ? {} : null
        }, 'twitter');
        const validation = validateContent({ text: args.text }, 'twitter');
        
        const characterCount = args.text.length;
        const isOptimalLength = characterCount >= 100 && characterCount <= 280;

        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              engagementScore: Math.round(engagement),
              characterCount,
              isOptimalLength,
              validation,
              recommendations: [
                !isOptimalLength && characterCount < 100 ? 'Consider adding more content for better engagement' : '',
                !args.hasMedia ? 'Adding media (images/GIFs) can increase engagement by up to 35%' : '',
                args.hasPoll ? 'Polls typically receive 2-3x more engagement' : 'Consider adding a poll for engagement',
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
    console.error('Twitter/X MCP Server running on stdio');
    console.error(`Pending Approval Dir: ${globalConfig.pendingApprovalDir}`);
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

main();
