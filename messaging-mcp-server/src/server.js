#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import https from 'https';
import http from 'http';
import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load configuration
const config = loadConfig();

// Initialize MCP Server
const server = new Server(
  {
    name: 'messaging-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Load messaging configuration
 */
function loadConfig() {
  const configPath = join(__dirname, '..', 'config', 'messaging-config.json');
  
  let config = {
    slack: {
      webhookUrl: process.env.SLACK_WEBHOOK_URL || '',
      botToken: process.env.SLACK_BOT_TOKEN || '',
      defaultChannel: process.env.SLACK_CHANNEL || '#general'
    },
    teams: {
      webhookUrl: process.env.TEAMS_WEBHOOK_URL || ''
    },
    defaultPlatform: process.env.DEFAULT_PLATFORM || 'slack'
  };
  
  // Try to load from config file
  if (existsSync(configPath)) {
    try {
      const fileContent = readFileSync(configPath, 'utf-8');
      const fileConfig = JSON.parse(fileContent);
      
      if (fileConfig.slack) {
        config.slack = { ...config.slack, ...fileConfig.slack };
      }
      if (fileConfig.teams) {
        config.teams = { ...config.teams, ...fileConfig.teams };
      }
      if (fileConfig.defaultPlatform) {
        config.defaultPlatform = fileConfig.defaultPlatform;
      }
    } catch (e) {
      console.error('Warning: Could not parse messaging config file:', e.message);
    }
  }
  
  return config;
}

/**
 * Send HTTP POST request
 */
function httpPost(url, data) {
  return new Promise((resolve, reject) => {
    const parsedUrl = new URL(url);
    const isHttps = parsedUrl.protocol === 'https:';
    const lib = isHttps ? https : http;
    
    const payload = JSON.stringify(data);
    
    const options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': payload.length
      }
    };
    
    const req = lib.request(url, options, (res) => {
      let responseData = '';
      res.on('data', chunk => responseData += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(responseData);
          resolve(result);
        } catch (e) {
          resolve({ raw: responseData });
        }
      });
    });
    
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

/**
 * Send Slack message via webhook
 */
async function sendSlackWebhook(message, options = {}) {
  const { webhookUrl = config.slack.webhookUrl } = options;
  
  if (!webhookUrl) {
    throw new Error('Slack webhook URL not configured');
  }
  
  const payload = {
    text: message.text,
    blocks: message.blocks || [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: message.text
        }
      }
    ]
  };
  
  // Add attachments if provided
  if (message.attachments) {
    payload.attachments = message.attachments;
  }
  
  const result = await httpPost(webhookUrl, payload);
  
  return {
    success: result.ok !== false,
    platform: 'slack',
    method: 'webhook',
    response: result
  };
}

/**
 * Send Slack message via Bot API
 */
async function sendSlackBot(message, options = {}) {
  const { botToken = config.slack.botToken, channel = config.slack.defaultChannel } = options;
  
  if (!botToken) {
    throw new Error('Slack bot token not configured');
  }
  
  const payload = {
    channel: channel,
    text: message.text,
    blocks: message.blocks
  };
  
  // Add attachments if provided
  if (message.attachments) {
    payload.attachments = message.attachments;
  }
  
  const result = await httpPost('https://slack.com/api/chat.postMessage', {
    ...payload
  }, {
    headers: {
      'Authorization': `Bearer ${botToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  return {
    success: result.ok !== false,
    platform: 'slack',
    method: 'bot',
    response: result
  };
}

/**
 * Send Microsoft Teams message via webhook
 */
async function sendTeamsWebhook(message, options = {}) {
  const { webhookUrl = config.teams.webhookUrl } = options;
  
  if (!webhookUrl) {
    throw new Error('Teams webhook URL not configured');
  }
  
  // Teams message format
  const payload = {
    '@type': 'MessageCard',
    '@context': 'http://schema.org/extensions',
    themeColor: message.color || '0076D7',
    summary: message.summary || message.text,
    sections: [
      {
        activityTitle: message.title || 'Notification',
        activitySubtitle: message.subtitle || '',
        activityImage: message.image || '',
        text: message.text,
        facts: message.facts || [],
        potentialAction: message.actions || []
      }
    ]
  };
  
  const result = await httpPost(webhookUrl, payload);
  
  return {
    success: result === 0 || result === '0' || (result && !result.error),
    platform: 'teams',
    method: 'webhook',
    response: result
  };
}

/**
 * Send briefing notification to Slack
 */
async function sendBriefingSlack(briefingData) {
  const {
    briefingPath,
    briefingUrl,
    period,
    recipients,
    customMessage
  } = briefingData;
  
  const filename = briefingPath?.split('/').pop() || 'Briefing';
  const date = new Date().toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
  
  const message = {
    text: `📋 *New CEO Briefing Available*\n\n${customMessage || `The ${period || 'weekly'} CEO briefing for ${date} is now ready for review.`}`,
    blocks: [
      {
        type: 'header',
        text: {
          type: 'plain_text',
          text: '📋 New CEO Briefing Available',
          emoji: true
        }
      },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `The *${period || 'weekly'}* CEO briefing for *${date}* is now ready for review.`
        }
      },
      {
        type: 'section',
        fields: [
          {
            type: 'mrkdwn',
            text: `*Period:*\n${period || 'Weekly'}`
          },
          {
            type: 'mrkdwn',
            text: `*Generated:*\n${new Date().toLocaleTimeString()}`
          }
        ]
      },
      {
        type: 'divider'
      },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: briefingUrl 
            ? `<${briefingUrl}|📄 View Briefing: ${filename}>`
            : `📄 Briefing: ${filename}`
        }
      }
    ],
    attachments: [
      {
        color: briefingUrl ? 'good' : 'warning',
        fields: [
          {
            title: 'Action Required',
            value: 'Please review the briefing and prepare for the week ahead.',
            short: false
          }
        ],
        footer: 'AI Employee Briefing System',
        ts: Math.floor(Date.now() / 1000)
      }
    ]
  };
  
  // Send via webhook or bot
  if (config.slack.webhookUrl) {
    return await sendSlackWebhook(message);
  } else if (config.slack.botToken) {
    return await sendSlackBot(message, { channel: recipients?.channel });
  } else {
    throw new Error('No Slack configuration found');
  }
}

/**
 * Send briefing notification to Teams
 */
async function sendBriefingTeams(briefingData) {
  const {
    briefingPath,
    briefingUrl,
    period,
    customMessage
  } = briefingData;
  
  const filename = briefingPath?.split('/').pop() || 'Briefing';
  const date = new Date().toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
  
  const message = {
    title: '📋 New CEO Briefing Available',
    subtitle: `${period || 'Weekly'} Briefing`,
    summary: `The ${period || 'weekly'} CEO briefing is now available`,
    color: '0076D7',
    text: customMessage || `The **${period || 'weekly'}** CEO briefing for **${date}** is now ready for review.`,
    facts: [
      {
        name: 'Period',
        value: period || 'Weekly'
      },
      {
        name: 'Generated',
        value: new Date().toLocaleString()
      },
      {
        name: 'File',
        value: filename
      }
    ],
    actions: briefingUrl ? [
      {
        '@type': 'OpenUri',
        'name': '📄 View Briefing',
        'targets': [
          {
            'os': 'default',
            'uri': briefingUrl
          }
        ]
      }
    ] : []
  };
  
  return await sendTeamsWebhook(message);
}

/**
 * Send notification to multiple platforms
 */
async function sendNotification(message, platforms = ['slack']) {
  const results = [];
  
  for (const platform of platforms) {
    try {
      let result;
      
      if (platform === 'slack') {
        result = await sendSlackWebhook(message);
      } else if (platform === 'teams') {
        result = await sendTeamsWebhook(message);
      } else {
        result = { success: false, error: `Unknown platform: ${platform}` };
      }
      
      results.push({ platform, ...result });
    } catch (error) {
      results.push({ 
        platform, 
        success: false, 
        error: error.message 
      });
    }
  }
  
  return results;
}

// Tool definitions
const TOOLS = [
  {
    name: 'messaging_send_slack',
    description: 'Send a message to Slack via webhook or bot',
    inputSchema: {
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: 'Message text (supports Slack mrkdwn)'
        },
        channel: {
          type: 'string',
          description: 'Slack channel (default: #general)'
        },
        blocks: {
          type: 'array',
          description: 'Slack blocks (optional, overrides text)'
        },
        attachments: {
          type: 'array',
          description: 'Slack attachments'
        },
        useBot: {
          type: 'boolean',
          description: 'Use bot API instead of webhook',
          default: false
        }
      },
      required: ['text']
    }
  },
  {
    name: 'messaging_send_teams',
    description: 'Send a message to Microsoft Teams via webhook',
    inputSchema: {
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: 'Message text (supports HTML)'
        },
        title: {
          type: 'string',
          description: 'Message title'
        },
        summary: {
          type: 'string',
          description: 'Message summary'
        },
        color: {
          type: 'string',
          description: 'Theme color (hex)',
          default: '0076D7'
        },
        facts: {
          type: 'array',
          description: 'Key-value facts',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              value: { type: 'string' }
            }
          }
        },
        actions: {
          type: 'array',
          description: 'Action buttons'
        }
      },
      required: ['text']
    }
  },
  {
    name: 'messaging_send_briefing_notification',
    description: 'Send CEO briefing notification to Slack and/or Teams',
    inputSchema: {
      type: 'object',
      properties: {
        briefingPath: {
          type: 'string',
          description: 'Path to the briefing file'
        },
        briefingUrl: {
          type: 'string',
          description: 'URL to access the briefing (optional)'
        },
        platforms: {
          type: 'array',
          description: 'Platforms to notify',
          items: {
            type: 'string',
            enum: ['slack', 'teams']
          },
          default: ['slack']
        },
        period: {
          type: 'string',
          description: 'Briefing period (weekly, monthly, etc.)',
          default: 'weekly'
        },
        customMessage: {
          type: 'string',
          description: 'Custom message to include'
        },
        recipients: {
          type: 'object',
          properties: {
            channel: { type: 'string' },
            users: { type: 'array', items: { type: 'string' } }
          }
        }
      },
      required: ['briefingPath']
    }
  },
  {
    name: 'messaging_test_connection',
    description: 'Test messaging connection for specified platforms',
    inputSchema: {
      type: 'object',
      properties: {
        platforms: {
          type: 'array',
          items: {
            type: 'string',
            enum: ['slack', 'teams']
          },
          default: ['slack']
        }
      }
    }
  }
];

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'messaging_send_slack': {
        const { useBot, channel, ...messageData } = args;
        
        const result = useBot 
          ? await sendSlackBot(messageData, { channel })
          : await sendSlackWebhook(messageData);
        
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'messaging_send_teams': {
        const result = await sendTeamsWebhook(args);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'messaging_send_briefing_notification': {
        const { platforms = ['slack'], ...briefingData } = args;
        const results = [];
        
        for (const platform of platforms) {
          try {
            let result;
            
            if (platform === 'slack') {
              result = await sendBriefingSlack(briefingData);
            } else if (platform === 'teams') {
              result = await sendBriefingTeams(briefingData);
            }
            
            results.push({ platform, ...result });
          } catch (error) {
            results.push({ platform, success: false, error: error.message });
          }
        }
        
        return {
          content: [{ 
            type: 'text', 
            text: JSON.stringify({
              success: results.some(r => r.success),
              results
            }, null, 2) 
          }]
        };
      }

      case 'messaging_test_connection': {
        const { platforms = ['slack'] } = args;
        const results = [];
        
        for (const platform of platforms) {
          try {
            let result;
            
            if (platform === 'slack') {
              if (config.slack.webhookUrl) {
                result = await sendSlackWebhook({
                  text: '🧪 *Test Message*\n\nThis is a test message from the Messaging MCP Server.'
                });
              } else if (config.slack.botToken) {
                result = await sendSlackBot({
                  text: '🧪 *Test Message*\n\nThis is a test message from the Messaging MCP Server.'
                });
              } else {
                result = { success: false, error: 'No Slack configuration found' };
              }
            } else if (platform === 'teams') {
              if (config.teams.webhookUrl) {
                result = await sendTeamsWebhook({
                  title: '🧪 Test Message',
                  text: 'This is a test message from the Messaging MCP Server.',
                  summary: 'Connection test'
                });
              } else {
                result = { success: false, error: 'No Teams configuration found' };
              }
            }
            
            results.push({ platform, ...result });
          } catch (error) {
            results.push({ platform, success: false, error: error.message });
          }
        }
        
        return {
          content: [{ 
            type: 'text', 
            text: JSON.stringify({
              success: results.some(r => r.success),
              results
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
    console.error('Messaging MCP Server running on stdio');
    console.error(`Slack: ${config.slack.webhookUrl ? 'webhook configured' : config.slack.botToken ? 'bot configured' : 'not configured'}`);
    console.error(`Teams: ${config.teams.webhookUrl ? 'webhook configured' : 'not configured'}`);
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

main();
