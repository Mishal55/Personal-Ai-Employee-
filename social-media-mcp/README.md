# Social Media MCP Servers

Model Context Protocol (MCP) servers for Facebook, Instagram, and Twitter/X with draft post creation and approval workflow.

## Features

- 📘 **Facebook MCP** - Draft posts, page management, insights
- 📷 **Instagram MCP** - Draft posts, Reels, hashtag generation
- 🐦 **Twitter/X MCP** - Draft tweets, threads, content analysis
- 🎯 **Orchestrator** - Cross-platform campaign management
- 📝 **Pending Approval** - Markdown files generated before publishing
- 📊 **Content Analysis** - Engagement scoring and recommendations

## Project Structure

```
social-media-mcp/
├── facebook/                    # Facebook MCP Server
│   ├── package.json
│   └── src/
│       └── server.js
├── instagram/                   # Instagram MCP Server
│   ├── package.json
│   └── src/
│       └── server.js
├── twitter/                     # Twitter/X MCP Server
│   ├── package.json
│   └── src/
│       └── server.js
├── orchestrator/                # Cross-platform Orchestrator
│   ├── package.json
│   └── src/
│       └── orchestrator.js
├── shared/                      # Shared utilities
│   ├── package.json
│   └── src/
│       ├── config.js
│       ├── content-formatter.js
│       └── pending-approval.js
├── config/
│   └── social-media-config.json.example
├── Pending_Approval/            # Generated approval files
└── README.md
```

## Installation

### Install each server

```bash
# Facebook
cd social-media-mcp/facebook
npm install

# Instagram
cd social-media-mcp/instagram
npm install

# Twitter
cd social-media-mcp/twitter
npm install

# Orchestrator
cd social-media-mcp/orchestrator
npm install
```

## Configuration

Copy and edit the configuration file:

```bash
cp config/social-media-config.json.example config/social-media-config.json
nano config/social-media-config.json
```

### Environment Variables

Alternatively, use environment variables:

```bash
# Facebook
export FB_APP_ID=your_app_id
export FB_APP_SECRET=your_app_secret
export FB_ACCESS_TOKEN=your_access_token
export FB_PAGE_ID=your_page_id

# Instagram
export IG_APP_ID=your_app_id
export IG_APP_SECRET=your_app_secret
export IG_ACCESS_TOKEN=your_access_token
export IG_ACCOUNT_ID=your_instagram_account_id

# Twitter
export TWITTER_API_KEY=your_api_key
export TWITTER_API_SECRET=your_api_secret
export TWITTER_ACCESS_TOKEN=your_access_token
export TWITTER_ACCESS_SECRET=your_access_secret
export TWITTER_BEARER_TOKEN=your_bearer_token
```

## Running the Servers

### Individual Servers

```bash
# Facebook
cd facebook && npm start

# Instagram
cd instagram && npm start

# Twitter
cd twitter && npm start

# Orchestrator
cd orchestrator && npm start
```

### MCP Client Configuration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "facebook": {
      "command": "node",
      "args": ["D:/Personal Ai Employee/social-media-mcp/facebook/src/server.js"],
      "env": {
        "FB_APP_ID": "...",
        "FB_ACCESS_TOKEN": "...",
        "FB_PAGE_ID": "..."
      }
    },
    "instagram": {
      "command": "node",
      "args": ["D:/Personal Ai Employee/social-media-mcp/instagram/src/server.js"],
      "env": {
        "IG_ACCESS_TOKEN": "...",
        "IG_ACCOUNT_ID": "..."
      }
    },
    "twitter": {
      "command": "node",
      "args": ["D:/Personal Ai Employee/social-media-mcp/twitter/src/server.js"],
      "env": {
        "TWITTER_BEARER_TOKEN": "..."
      }
    },
    "social-orchestrator": {
      "command": "node",
      "args": ["D:/Personal Ai Employee/social-media-mcp/orchestrator/src/orchestrator.js"]
    }
  }
}
```

## Available Tools

### Facebook MCP

| Tool | Description |
|------|-------------|
| `facebook_create_draft_post` | Create draft post (generates approval file) |
| `facebook_publish_post` | Publish post immediately |
| `facebook_get_page_info` | Get page information |
| `facebook_get_recent_posts` | Get recent posts |
| `facebook_get_insights` | Get page analytics |
| `facebook_search_pages` | Search for pages |
| `facebook_analyze_content` | Analyze content for engagement |

### Instagram MCP

| Tool | Description |
|------|-------------|
| `instagram_create_draft_post` | Create draft post (generates approval file) |
| `instagram_publish_media` | Publish media container |
| `instagram_create_reel` | Create draft Reel |
| `instagram_get_account_info` | Get account information |
| `instagram_get_recent_media` | Get recent posts |
| `instagram_get_media_insights` | Get post analytics |
| `instagram_generate_hashtags` | Generate optimal hashtags |
| `instagram_analyze_content` | Analyze content for engagement |

### Twitter/X MCP

| Tool | Description |
|------|-------------|
| `twitter_create_draft_tweet` | Create draft tweet (generates approval file) |
| `twitter_create_draft_thread` | Create draft thread |
| `twitter_split_into_thread` | Split long content into thread |
| `twitter_publish_tweet` | Publish tweet |
| `twitter_get_user_info` | Get user information |
| `twitter_get_recent_tweets` | Get recent tweets |
| `twitter_search_tweets` | Search tweets |
| `twitter_generate_hashtags` | Generate hashtag suggestions |
| `twitter_analyze_content` | Analyze tweet for engagement |

### Orchestrator

| Tool | Description |
|------|-------------|
| `social_create_cross_platform_campaign` | Create campaign across all platforms |
| `social_schedule_posts` | Schedule draft posts |
| `social_get_all_drafts` | List all drafts with filters |
| `social_delete_draft` | Delete a draft |
| `social_generate_content_calendar` | Generate weekly calendar |
| `social_analyze_cross_platform` | Analyze content across platforms |
| `social_generate_platform_variations` | Generate platform-specific content |

## Approval Workflow

All draft creation tools generate markdown files in `/Pending_Approval`:

### Facebook Post Approval File

```
Pending_Approval/
└── FB_POST_2026-02-27T09-30-00.md
```

Contains:
- Post content preview
- Character count
- Target audience
- Approval checklist
- Execution details

### Instagram Post Approval File

```
Pending_Approval/
└── IG_POST_2026-02-27T09-30-00.md
```

Contains:
- Caption and hashtags
- Media preview
- Character/hashtag counts
- Approval checklist

### Twitter Post Approval File

```
Pending_Approval/
└── TW_POST_2026-02-27T09-30-00.md
```

Contains:
- Tweet text
- Character count
- Thread info (if applicable)
- Approval checklist

### Cross-Platform Summary

```
Pending_Approval/
└── CROSS_PLATFORM_SUMMARY_2026-02-27T09-30-00.md
```

Contains:
- Overview of all platform posts
- Individual post summaries
- Bulk approval checklist

## Usage Examples

### Create Facebook Draft Post

```javascript
{
  "name": "facebook_create_draft_post",
  "arguments": {
    "message": "Exciting news! We're launching our new product today! 🚀",
    "link": "https://example.com/product",
    "picture": "https://example.com/image.jpg",
    "generateApprovalFile": true
  }
}
```

### Create Instagram Post with Hashtags

```javascript
{
  "name": "instagram_create_draft_post",
  "arguments": {
    "caption": "Behind the scenes at our office! 💼",
    "mediaUrl": "https://example.com/office.jpg",
    "mediaType": "IMAGE",
    "hashtags": ["office", "team", "work"],
    "generateApprovalFile": true
  }
}
```

### Create Twitter Thread

```javascript
{
  "name": "twitter_create_draft_thread",
  "arguments": {
    "tweets": [
      {
        "text": "🧵 Thread: Here's everything you need to know about our new feature..."
      },
      {
        "text": "1/ First, let's talk about why we built this. Our users asked for..."
      },
      {
        "text": "2/ The development process took 3 months with our amazing team..."
      },
      {
        "text": "3/ Ready to try it? Visit https://example.com to get started!"
      }
    ],
    "generateApprovalFile": true
  }
}
```

### Cross-Platform Campaign

```javascript
{
  "name": "social_create_cross_platform_campaign",
  "arguments": {
    "baseContent": {
      "message": "Big announcement coming tomorrow! Stay tuned! 🎉",
      "link": "https://example.com/announcement",
      "mediaUrl": "https://example.com/teaser.jpg",
      "hashtags": ["announcement", "comingsoon", "excited"]
    },
    "platforms": ["facebook", "instagram", "twitter"],
    "campaignName": "Product Launch 2026",
    "generateApprovalFiles": true
  }
}
```

## Content Analysis

Each platform includes content analysis tools:

### Engagement Scoring

Scores content 0-100 based on:
- Hashtag usage
- Media inclusion
- Content length
- Question inclusion
- Platform-specific factors

### Recommendations

- Optimal character counts
- Hashtag suggestions
- Media recommendations
- Posting time suggestions

## Platform Limits

| Platform | Content Limit | Hashtags | Media |
|----------|--------------|----------|-------|
| Facebook | 63,206 chars | 30 max | 10 photos/videos |
| Instagram | 2,200 chars | 30 max | 10 carousel items |
| Twitter | 280 chars | 30 max | 4 media items |

## API Requirements

### Facebook
- Facebook App with Graph API access
- Page Access Token with `pages_manage_posts` permission

### Instagram
- Instagram Business Account
- Facebook App with Instagram Graph API
- Access Token with `instagram_basic`, `instagram_content_publish`

### Twitter
- Twitter Developer Account
- API Key, Secret, Access Token, Access Secret
- Bearer Token for API v2

## Troubleshooting

**"Invalid access token"**
- Regenerate tokens in developer portal
- Check token permissions
- Verify token hasn't expired

**"Approval file not generated"**
- Check `pendingApprovalDir` configuration
- Ensure directory is writable
- Set `autoGenerateApprovalFiles: true`

**"Content exceeds limit"**
- Use content analysis tools before posting
- Check platform-specific limits
- Use thread splitting for Twitter

## Security Notes

⚠️ **Never commit credentials:**
- Add `config/social-media-config.json` to `.gitignore`
- Use environment variables in production
- Rotate tokens regularly

## License

MIT
