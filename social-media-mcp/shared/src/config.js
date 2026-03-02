import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Load configuration for social media MCP servers
 */
export function loadConfig(platform = null) {
  const configPaths = [
    join(__dirname, '..', '..', 'config', 'social-media-config.json'),
    join(__dirname, '..', 'config', 'social-media-config.json'),
    join(__dirname, '..', '..', '..', 'config', 'social-media-config.json')
  ];

  let config = {
    facebook: {
      appId: process.env.FB_APP_ID || '',
      appSecret: process.env.FB_APP_SECRET || '',
      accessToken: process.env.FB_ACCESS_TOKEN || '',
      pageId: process.env.FB_PAGE_ID || '',
      apiVersion: 'v19.0'
    },
    instagram: {
      appId: process.env.IG_APP_ID || '',
      appSecret: process.env.IG_APP_SECRET || '',
      accessToken: process.env.IG_ACCESS_TOKEN || '',
      instagramAccountId: process.env.IG_ACCOUNT_ID || '',
      apiVersion: 'v19.0'
    },
    twitter: {
      apiKey: process.env.TWITTER_API_KEY || '',
      apiSecret: process.env.TWITTER_API_SECRET || '',
      accessToken: process.env.TWITTER_ACCESS_TOKEN || '',
      accessSecret: process.env.TWITTER_ACCESS_SECRET || '',
      bearerToken: process.env.TWITTER_BEARER_TOKEN || '',
      apiVersion: '2'
    },
    pendingApprovalDir: process.env.PENDING_APPROVAL_DIR || 
      join(__dirname, '..', '..', 'Pending_Approval'),
    autoGenerateApprovalFiles: true
  };

  // Try to load from config file
  for (const configPath of configPaths) {
    if (existsSync(configPath)) {
      try {
        const fileContent = readFileSync(configPath, 'utf-8');
        const fileConfig = JSON.parse(fileContent);
        
        // Deep merge
        if (fileConfig.facebook) {
          config.facebook = { ...config.facebook, ...fileConfig.facebook };
        }
        if (fileConfig.instagram) {
          config.instagram = { ...config.instagram, ...fileConfig.instagram };
        }
        if (fileConfig.twitter) {
          config.twitter = { ...config.twitter, ...fileConfig.twitter };
        }
        if (fileConfig.pendingApprovalDir) {
          config.pendingApprovalDir = fileConfig.pendingApprovalDir;
        }
        if (fileConfig.autoGenerateApprovalFiles !== undefined) {
          config.autoGenerateApprovalFiles = fileConfig.autoGenerateApprovalFiles;
        }
      } catch (e) {
        console.error('Warning: Could not parse config file:', configPath, e.message);
      }
      break;
    }
  }

  // Return specific platform config if requested
  if (platform && config[platform]) {
    return config[platform];
  }

  return config;
}

/**
 * Validate that required credentials are present
 */
export function validateCredentials(platform, config) {
  const required = {
    facebook: ['appId', 'appSecret', 'accessToken', 'pageId'],
    instagram: ['appId', 'appSecret', 'accessToken', 'instagramAccountId'],
    twitter: ['apiKey', 'apiSecret', 'accessToken', 'accessSecret']
  };

  const platformRequired = required[platform];
  if (!platformRequired) {
    return { valid: false, error: `Unknown platform: ${platform}` };
  }

  const missing = platformRequired.filter(key => !config[key]);
  
  if (missing.length > 0) {
    return {
      valid: false,
      error: `Missing credentials: ${missing.join(', ')}`,
      missing
    };
  }

  return { valid: true };
}

export default {
  loadConfig,
  validateCredentials
};
