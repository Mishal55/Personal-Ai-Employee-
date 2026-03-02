#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import nodemailer from 'nodemailer';
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
    name: 'email-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Load email configuration
 */
function loadConfig() {
  const configPath = join(__dirname, '..', 'config', 'email-config.json');
  
  let config = {
    smtp: {
      host: process.env.SMTP_HOST || 'smtp.gmail.com',
      port: parseInt(process.env.SMTP_PORT) || 587,
      secure: process.env.SMTP_SECURE === 'true',
      auth: {
        user: process.env.SMTP_USER || '',
        pass: process.env.SMTP_PASS || ''
      }
    },
    from: process.env.EMAIL_FROM || '',
    defaultRecipients: {
      to: process.env.EMAIL_TO?.split(',') || [],
      cc: process.env.EMAIL_CC?.split(',') || [],
      bcc: process.env.EMAIL_BCC?.split(',') || []
    }
  };
  
  // Try to load from config file
  if (existsSync(configPath)) {
    try {
      const fileContent = readFileSync(configPath, 'utf-8');
      const fileConfig = JSON.parse(fileContent);
      
      if (fileConfig.smtp) {
        config.smtp = { ...config.smtp, ...fileConfig.smtp };
      }
      if (fileConfig.from) {
        config.from = fileConfig.from;
      }
      if (fileConfig.defaultRecipients) {
        config.defaultRecipients = { ...config.defaultRecipients, ...fileConfig.defaultRecipients };
      }
    } catch (e) {
      console.error('Warning: Could not parse email config file:', e.message);
    }
  }
  
  return config;
}

/**
 * Create email transporter
 */
function createTransporter() {
  const transporter = nodemailer.createTransport({
    host: config.smtp.host,
    port: config.smtp.port,
    secure: config.smtp.secure,
    auth: config.smtp.auth,
    tls: {
      rejectUnauthorized: config.smtp.secure
    }
  });
  
  return transporter;
}

/**
 * Send email with optional attachments
 */
async function sendEmail(emailData) {
  const {
    to,
    cc,
    bcc,
    subject,
    text,
    html,
    attachments = []
  } = emailData;
  
  const transporter = createTransporter();
  
  const mailOptions = {
    from: config.from || config.smtp.auth.user,
    to: Array.isArray(to) ? to.join(',') : to,
    cc: cc ? (Array.isArray(cc) ? cc.join(',') : cc) : undefined,
    bcc: bcc ? (Array.isArray(bcc) ? bcc.join(',') : bcc) : undefined,
    subject: subject,
    text: text,
    html: html || text?.replace(/\n/g, '<br>'),
    attachments: attachments.map(att => ({
      filename: att.filename || att.path?.split('/').pop() || 'attachment',
      path: att.path,
      content: att.content,
      contentType: att.contentType
    })).filter(att => att.path || att.content)
  };
  
  const info = await transporter.sendMail(mailOptions);
  
  return {
    success: true,
    messageId: info.messageId,
    accepted: info.accepted,
    rejected: info.rejected || []
  };
}

/**
 * Send briefing email
 */
async function sendBriefingEmail(briefingData) {
  const {
    recipients,
    subject = 'Weekly CEO Briefing',
    briefingPath,
    additionalMessage
  } = briefingData;
  
  // Read the briefing file
  if (!existsSync(briefingPath)) {
    throw new Error(`Briefing file not found: ${briefingPath}`);
  }
  
  const briefingContent = readFileSync(briefingPath, 'utf-8');
  
  // Create email body
  const emailBody = additionalMessage || `
Dear Team,

Please find attached the Weekly CEO Briefing.

Best regards,
AI Employee System
  `.trim();
  
  const result = await sendEmail({
    to: recipients.to || config.defaultRecipients.to,
    cc: recipients.cc || config.defaultRecipients.cc,
    bcc: recipients.bcc || config.defaultRecipients.bcc,
    subject: subject,
    text: emailBody,
    attachments: [
      {
        path: briefingPath,
        filename: briefingPath.split('/').pop()
      }
    ]
  });
  
  return result;
}

// Tool definitions
const TOOLS = [
  {
    name: 'email_send',
    description: 'Send an email with optional attachments',
    inputSchema: {
      type: 'object',
      properties: {
        to: {
          oneOf: [
            { type: 'string' },
            { type: 'array', items: { type: 'string' } }
          ],
          description: 'Recipient email address(es)'
        },
        cc: {
          oneOf: [
            { type: 'string' },
            { type: 'array', items: { type: 'string' } }
          ],
          description: 'CC email address(es)'
        },
        bcc: {
          oneOf: [
            { type: 'string' },
            { type: 'array', items: { type: 'string' } }
          ],
          description: 'BCC email address(es)'
        },
        subject: {
          type: 'string',
          description: 'Email subject'
        },
        text: {
          type: 'string',
          description: 'Plain text email body'
        },
        html: {
          type: 'string',
          description: 'HTML email body'
        },
        attachments: {
          type: 'array',
          description: 'File attachments',
          items: {
            type: 'object',
            properties: {
              path: { type: 'string', description: 'Path to file' },
              filename: { type: 'string', description: 'Custom filename' },
              contentType: { type: 'string', description: 'MIME type' }
            }
          }
        }
      },
      required: ['to', 'subject', 'text']
    }
  },
  {
    name: 'email_send_briefing',
    description: 'Send CEO briefing email with markdown attachment',
    inputSchema: {
      type: 'object',
      properties: {
        recipients: {
          type: 'object',
          properties: {
            to: {
              oneOf: [
                { type: 'string' },
                { type: 'array', items: { type: 'string' } }
              ],
              description: 'To addresses'
            },
            cc: {
              oneOf: [
                { type: 'string' },
                { type: 'array', items: { type: 'string' } }
              ],
              description: 'CC addresses'
            },
            bcc: {
              oneOf: [
                { type: 'string' },
                { type: 'array', items: { type: 'string' } }
              ],
              description: 'BCC addresses'
            }
          }
        },
        subject: {
          type: 'string',
          description: 'Email subject',
          default: 'Weekly CEO Briefing'
        },
        briefingPath: {
          type: 'string',
          description: 'Path to the briefing markdown file'
        },
        additionalMessage: {
          type: 'string',
          description: 'Additional message to include in email body'
        }
      },
      required: ['briefingPath']
    }
  },
  {
    name: 'email_test_connection',
    description: 'Test email connection by sending a test email',
    inputSchema: {
      type: 'object',
      properties: {
        testRecipient: {
          type: 'string',
          description: 'Email address to send test to'
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
      case 'email_send': {
        const result = await sendEmail(args);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'email_send_briefing': {
        const result = await sendBriefingEmail(args);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
        };
      }

      case 'email_test_connection': {
        const testRecipient = args.testRecipient || config.defaultRecipients.to[0];
        if (!testRecipient) {
          return {
            content: [{ type: 'text', text: JSON.stringify({ error: 'No test recipient specified' }, null, 2) }],
            isError: true
          };
        }
        
        const result = await sendEmail({
          to: testRecipient,
          subject: 'Email MCP Server - Test Connection',
          text: 'This is a test email from the Email MCP Server. Connection successful!'
        });
        
        return {
          content: [{ type: 'text', text: JSON.stringify({
            success: true,
            message: 'Test email sent successfully',
            ...result
          }, null, 2) }]
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
    console.error('Email MCP Server running on stdio');
    console.error(`SMTP Host: ${config.smtp.host}`);
    console.error(`From: ${config.from || config.smtp.auth.user}`);
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

main();
