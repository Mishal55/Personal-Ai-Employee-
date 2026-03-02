#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Social Media MCP Server - Gold Tier Feature

Unified MCP server for Facebook, Instagram, and Twitter posting.
Includes content summary generation and cross-platform scheduling.

Configuration:
    Set environment variables for each platform:
    - FACEBOOK_PAGE_ID, FACEBOOK_ACCESS_TOKEN
    - INSTAGRAM_BUSINESS_ACCOUNT_ID, INSTAGRAM_ACCESS_TOKEN
    - TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET

Usage:
    python social_media_mcp.py  # Run as stdio MCP server

Tools:
    - create_facebook_post: Create Facebook page post
    - create_instagram_post: Create Instagram post
    - create_twitter_tweet: Create Twitter tweet
    - schedule_social_post: Schedule post for multiple platforms
    - list_scheduled_posts: List all scheduled posts
    - generate_content_summary: Generate content summary from source
    - cross_post: Post same content to multiple platforms
"""

import argparse
import json
import os
import sys
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List


# Configuration
VAULT_PATH = Path(os.environ.get('AI_VAULT_PATH', r'D:\Personal Ai Employee\AI_Employee_Vault'))
SOCIAL_STATE_FILE = VAULT_PATH / 'watchers' / 'social_media_state.json'
SOCIAL_LOG_FILE = VAULT_PATH / 'Logs' / 'social_media_mcp.log'
SOCIAL_DRAFTS_PATH = VAULT_PATH / 'watchers' / 'facebook' / 'drafts'
SOCIAL_SCHEDULED_PATH = VAULT_PATH / 'watchers' / 'facebook' / 'scheduled'
SOCIAL_PUBLISHED_PATH = VAULT_PATH / 'watchers' / 'facebook' / 'published'

for path in [SOCIAL_DRAFTS_PATH, SOCIAL_SCHEDULED_PATH, SOCIAL_PUBLISHED_PATH]:
    path.mkdir(parents=True, exist_ok=True)


def log_message(message: str, level: str = "INFO"):
    """Log a message to the log file."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    with open(SOCIAL_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def generate_post_id(platform: str, content: str) -> str:
    """Generate a unique post ID."""
    hash_input = f"{platform}_{content}_{datetime.now().isoformat()}"
    return f"{platform.upper()}_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"


def load_state() -> dict:
    """Load social media state from file."""
    if SOCIAL_STATE_FILE.exists():
        with open(SOCIAL_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'posts': [], 'last_sync': None}


def save_state(state: dict):
    """Save social media state to file."""
    with open(SOCIAL_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)


def format_post_markdown(post: dict) -> str:
    """Format a post as markdown for the vault."""
    platforms = ', '.join(post.get('platforms', []))
    
    return f"""---
id: {post['id']}
type: social_media_post
platforms: {platforms}
status: {post['status']}
created_at: {post['created_at']}
scheduled_time: {post.get('scheduled_time', 'Not scheduled')}
content_hash: {post.get('content_hash', '')}
---

# Social Media Post

## Content

{post['content']}

## Platforms

{chr(10).join(f"- [ ] {p}" for p in post.get('platforms', []))}

## Media

{'![Image](' + post['image_path'] + ')' if post.get('image_path') else '*No image*'}

---

## Approval Workflow

- [ ] Content reviewed for brand voice
- [ ] Hashtags are relevant
- [ ] Image is appropriate
- [ ] Scheduled time is optimal
- [ ] Cross-platform consistency checked

---

*Managed by Social Media MCP Server (Gold Tier)*
"""


# ============================================================================
# Platform-Specific Operations (Simulated - Add real API calls for production)
# ============================================================================

def create_facebook_post(content: str, image_path: Optional[str] = None,
                         scheduled_time: Optional[str] = None) -> dict:
    """Create a Facebook page post."""
    post_id = generate_post_id('fb', content)
    
    post = {
        'id': post_id,
        'platforms': ['facebook'],
        'content': content,
        'image_path': image_path,
        'scheduled_time': scheduled_time,
        'status': 'draft',
        'created_at': datetime.now().isoformat(),
        'content_hash': hashlib.md5(content.encode()).hexdigest()
    }
    
    # Save draft
    draft_file = SOCIAL_DRAFTS_PATH / f"{post_id}.md"
    draft_file.write_text(format_post_markdown(post), encoding='utf-8')
    
    # Update state
    state = load_state()
    state['posts'].append(post)
    save_state(state)
    
    log_message(f"Created Facebook draft: {post_id}")
    
    return {
        'post_id': post_id,
        'platform': 'facebook',
        'status': 'draft',
        'message': 'Facebook post draft created. Requires approval before publishing.'
    }


def create_instagram_post(content: str, hashtags: Optional[List[str]] = None,
                          image_path: Optional[str] = None,
                          scheduled_time: Optional[str] = None) -> dict:
    """Create an Instagram post."""
    post_id = generate_post_id('ig', content)
    
    # Add hashtags to content
    full_content = content
    if hashtags:
        hashtag_str = ' '.join(f'#{tag}' for tag in hashtags)
        full_content = f"{content}\n\n{hashtag_str}"
    
    post = {
        'id': post_id,
        'platforms': ['instagram'],
        'content': full_content,
        'hashtags': hashtags or [],
        'image_path': image_path,
        'scheduled_time': scheduled_time,
        'status': 'draft',
        'created_at': datetime.now().isoformat(),
        'content_hash': hashlib.md5(content.encode()).hexdigest()
    }
    
    # Save draft
    draft_file = SOCIAL_DRAFTS_PATH / f"{post_id}.md"
    draft_file.write_text(format_post_markdown(post), encoding='utf-8')
    
    # Update state
    state = load_state()
    state['posts'].append(post)
    save_state(state)
    
    log_message(f"Created Instagram draft: {post_id}")
    
    return {
        'post_id': post_id,
        'platform': 'instagram',
        'status': 'draft',
        'hashtags': hashtags,
        'message': 'Instagram post draft created. Requires approval before publishing.'
    }


def create_twitter_tweet(content: str, scheduled_time: Optional[str] = None) -> dict:
    """Create a Twitter tweet."""
    # Check character limit
    if len(content) > 280:
        return {'error': 'Tweet content exceeds 280 character limit'}
    
    post_id = generate_post_id('tw', content)
    
    post = {
        'id': post_id,
        'platforms': ['twitter'],
        'content': content,
        'scheduled_time': scheduled_time,
        'status': 'draft',
        'created_at': datetime.now().isoformat(),
        'content_hash': hashlib.md5(content.encode()).hexdigest()
    }
    
    # Save draft
    draft_file = SOCIAL_DRAFTS_PATH / f"{post_id}.md"
    draft_file.write_text(format_post_markdown(post), encoding='utf-8')
    
    # Update state
    state = load_state()
    state['posts'].append(post)
    save_state(state)
    
    log_message(f"Created Twitter draft: {post_id}")
    
    return {
        'post_id': post_id,
        'platform': 'twitter',
        'status': 'draft',
        'message': 'Twitter draft created. Requires approval before publishing.'
    }


def schedule_post(post_id: str, scheduled_time: str,
                  platforms: Optional[List[str]] = None) -> dict:
    """Schedule a post for publishing."""
    state = load_state()
    
    for post in state['posts']:
        if post['id'] == post_id:
            if post['status'] != 'draft':
                return {'error': f"Post is not in draft status: {post['status']}"}
            
            post['scheduled_time'] = scheduled_time
            post['status'] = 'scheduled'
            post['updated_at'] = datetime.now().isoformat()
            
            if platforms:
                post['platforms'] = platforms
            
            # Move file
            old_file = SOCIAL_DRAFTS_PATH / f"{post_id}.md"
            new_file = SOCIAL_SCHEDULED_PATH / f"{post_id}.md"
            
            if old_file.exists():
                content = old_file.read_text(encoding='utf-8')
                content = content.replace('status: draft', 'status: scheduled')
                content = content.replace(f"scheduled_time: Not scheduled", f"scheduled_time: {scheduled_time}")
                new_file.write_text(content, encoding='utf-8')
                old_file.unlink()
            
            save_state(state)
            log_message(f"Scheduled post {post_id} for {scheduled_time}")
            
            return {
                'post_id': post_id,
                'status': 'scheduled',
                'scheduled_time': scheduled_time,
                'platforms': post['platforms'],
                'message': f"Post scheduled for {scheduled_time}"
            }
    
    return {'error': f"Post not found: {post_id}"}


def publish_post(post_id: str) -> dict:
    """Publish a post (simulated)."""
    state = load_state()
    
    for post in state['posts']:
        if post['id'] == post_id:
            if post['status'] not in ['draft', 'scheduled']:
                return {'error': f"Post status not ready: {post['status']}"}
            
            # Simulate publishing to each platform
            published_to = []
            for platform in post.get('platforms', []):
                # In production, call actual API here
                published_to.append(platform)
                log_message(f"Published to {platform}: {post_id}")
            
            post['status'] = 'published'
            post['published_at'] = datetime.now().isoformat()
            post['published_platforms'] = published_to
            
            # Move file
            old_file = SOCIAL_SCHEDULED_PATH / f"{post_id}.md"
            if not old_file.exists():
                old_file = SOCIAL_DRAFTS_PATH / f"{post_id}.md"
            
            new_file = SOCIAL_PUBLISHED_PATH / f"{post_id}.md"
            
            if old_file.exists():
                content = old_file.read_text(encoding='utf-8')
                content = content.replace(f"status: {post['status']}", 'status: published')
                new_file.write_text(content, encoding='utf-8')
                old_file.unlink()
            
            save_state(state)
            log_message(f"Published post {post_id}")
            
            return {
                'post_id': post_id,
                'status': 'published',
                'published_at': post['published_at'],
                'platforms': published_to,
                'message': f"Post published to {', '.join(published_to)}"
            }
    
    return {'error': f"Post not found: {post_id}"}


def cross_post(content: str, platforms: List[str],
               hashtags: Optional[List[str]] = None,
               image_path: Optional[str] = None,
               scheduled_time: Optional[str] = None) -> dict:
    """Create and schedule a post across multiple platforms."""
    post_id = generate_post_id('cross', content)
    
    # Adapt content for each platform
    platform_content = {}
    for platform in platforms:
        if platform == 'twitter' and len(content) > 280:
            # Truncate for Twitter
            platform_content[platform] = content[:277] + '...'
        elif platform == 'instagram' and hashtags:
            hashtag_str = ' '.join(f'#{tag}' for tag in hashtags)
            platform_content[platform] = f"{content}\n\n{hashtag_str}"
        else:
            platform_content[platform] = content
    
    post = {
        'id': post_id,
        'platforms': platforms,
        'content': content,
        'platform_content': platform_content,
        'hashtags': hashtags or [],
        'image_path': image_path,
        'scheduled_time': scheduled_time,
        'status': 'draft',
        'created_at': datetime.now().isoformat(),
        'content_hash': hashlib.md5(content.encode()).hexdigest()
    }
    
    # Save draft
    draft_file = SOCIAL_DRAFTS_PATH / f"{post_id}.md"
    draft_file.write_text(format_post_markdown(post), encoding='utf-8')
    
    # Update state
    state = load_state()
    state['posts'].append(post)
    save_state(state)
    
    log_message(f"Created cross-post draft: {post_id} for {len(platforms)} platforms")
    
    return {
        'post_id': post_id,
        'platforms': platforms,
        'status': 'draft',
        'message': f"Cross-post draft created for {', '.join(platforms)}. Requires approval."
    }


def list_posts(status: Optional[str] = None,
               platform: Optional[str] = None,
               limit: int = 20) -> dict:
    """List social media posts."""
    state = load_state()
    posts = state.get('posts', [])
    
    if status:
        posts = [p for p in posts if p['status'] == status]
    
    if platform:
        posts = [p for p in posts if platform in p.get('platforms', [])]
    
    # Format and limit
    formatted = [{
        'id': p['id'],
        'platforms': p.get('platforms', []),
        'status': p['status'],
        'created_at': p['created_at'],
        'scheduled_time': p.get('scheduled_time'),
        'content_preview': p['content'][:50] + '...' if len(p['content']) > 50 else p['content']
    } for p in posts[-limit:]]
    
    return {'posts': formatted, 'count': len(formatted)}


def generate_content_summary(source_content: str,
                             platform: str = 'all',
                             tone: str = 'professional') -> dict:
    """
    Generate platform-optimized content summaries.
    
    Args:
        source_content: Original content to summarize
        platform: Target platform (facebook, instagram, twitter, linkedin, all)
        tone: Content tone (professional, casual, enthusiastic)
    
    Returns:
        Optimized content for each platform
    """
    # Simple summarization logic (in production, use AI)
    words = source_content.split()
    
    summaries = {}
    
    # Twitter: 280 chars max
    twitter_content = source_content[:277] + '...' if len(source_content) > 280 else source_content
    
    # Facebook: Can be longer, but 100-150 chars optimal
    fb_content = source_content[:150] + '...' if len(source_content) > 150 else source_content
    
    # Instagram: Focus on visual storytelling
    ig_content = source_content[:200] + '...' if len(source_content) > 200 else source_content
    
    # LinkedIn: Professional tone
    li_content = source_content[:300] + '...' if len(source_content) > 300 else source_content
    
    if platform in ['twitter', 'all']:
        summaries['twitter'] = {
            'content': twitter_content,
            'character_count': len(twitter_content),
            'optimal': len(twitter_content) <= 280
        }
    
    if platform in ['facebook', 'all']:
        summaries['facebook'] = {
            'content': fb_content,
            'character_count': len(fb_content),
            'optimal': len(fb_content) <= 150
        }
    
    if platform in ['instagram', 'all']:
        summaries['instagram'] = {
            'content': ig_content,
            'character_count': len(ig_content),
            'suggested_hashtags': ['#Content', '#Social', '#GoldTier']
        }
    
    if platform in ['linkedin', 'all']:
        summaries['linkedin'] = {
            'content': li_content,
            'character_count': len(li_content),
            'tone': tone
        }
    
    return {
        'source_length': len(source_content),
        'source_words': len(words),
        'summaries': summaries
    }


def cancel_post(post_id: str) -> dict:
    """Cancel a scheduled post."""
    state = load_state()
    
    for post in state['posts']:
        if post['id'] == post_id:
            if post['status'] != 'scheduled':
                return {'error': f"Post is not scheduled: {post['status']}"}
            
            post['status'] = 'draft'
            post['scheduled_time'] = None
            post['updated_at'] = datetime.now().isoformat()
            
            # Move file back
            old_file = SOCIAL_SCHEDULED_PATH / f"{post_id}.md"
            new_file = SOCIAL_DRAFTS_PATH / f"{post_id}.md"
            
            if old_file.exists():
                content = old_file.read_text(encoding='utf-8')
                content = content.replace('status: scheduled', 'status: draft')
                new_file.write_text(content, encoding='utf-8')
                old_file.unlink()
            
            save_state(state)
            log_message(f"Cancelled post {post_id}")
            
            return {
                'post_id': post_id,
                'status': 'draft',
                'message': 'Post cancelled and returned to drafts.'
            }
    
    return {'error': f"Post not found: {post_id}"}


# ============================================================================
# MCP Server Implementation
# ============================================================================

class SocialMediaMCPServer:
    """MCP Server for Social Media management."""
    
    def __init__(self):
        self.tools = {
            'create_facebook_post': {
                'description': 'Create a Facebook page post',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'content': {'type': 'string', 'description': 'Post content'},
                        'image_path': {'type': 'string', 'description': 'Path to image'},
                        'scheduled_time': {'type': 'string', 'description': 'ISO 8601 datetime'}
                    },
                    'required': ['content']
                }
            },
            'create_instagram_post': {
                'description': 'Create an Instagram post',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'content': {'type': 'string'},
                        'hashtags': {'type': 'array', 'items': {'type': 'string'}},
                        'image_path': {'type': 'string'},
                        'scheduled_time': {'type': 'string'}
                    },
                    'required': ['content']
                }
            },
            'create_twitter_tweet': {
                'description': 'Create a Twitter tweet',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'content': {'type': 'string', 'description': 'Tweet content (max 280 chars)'},
                        'scheduled_time': {'type': 'string'}
                    },
                    'required': ['content']
                }
            },
            'schedule_post': {
                'description': 'Schedule a post for publishing',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_id': {'type': 'string'},
                        'scheduled_time': {'type': 'string'},
                        'platforms': {'type': 'array', 'items': {'type': 'string'}}
                    },
                    'required': ['post_id', 'scheduled_time']
                }
            },
            'publish_post': {
                'description': 'Publish a post immediately',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_id': {'type': 'string'}
                    },
                    'required': ['post_id']
                }
            },
            'list_posts': {
                'description': 'List social media posts',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'status': {'type': 'string', 'enum': ['draft', 'scheduled', 'published']},
                        'platform': {'type': 'string'},
                        'limit': {'type': 'integer', 'default': 20}
                    }
                }
            },
            'cross_post': {
                'description': 'Post same content to multiple platforms',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'content': {'type': 'string'},
                        'platforms': {'type': 'array', 'items': {'type': 'string'}},
                        'hashtags': {'type': 'array', 'items': {'type': 'string'}},
                        'image_path': {'type': 'string'},
                        'scheduled_time': {'type': 'string'}
                    },
                    'required': ['content', 'platforms']
                }
            },
            'generate_content_summary': {
                'description': 'Generate platform-optimized content summaries',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'source_content': {'type': 'string'},
                        'platform': {'type': 'string', 'default': 'all'},
                        'tone': {'type': 'string', 'default': 'professional'}
                    },
                    'required': ['source_content']
                }
            },
            'cancel_post': {
                'description': 'Cancel a scheduled post',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_id': {'type': 'string'}
                    },
                    'required': ['post_id']
                }
            }
        }
    
    def handle_request(self, request: dict) -> dict:
        """Handle an MCP JSON-RPC request."""
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        try:
            if method == 'tools/list':
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'tools': [
                            {'name': name, **tool}
                            for name, tool in self.tools.items()
                        ]
                    }
                }
            
            elif method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                
                result = self.call_tool(tool_name, arguments)
                
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'content': [{'type': 'text', 'text': json.dumps(result, indent=2, default=str)}]
                    }
                }
            
            elif method == 'initialize':
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'protocolVersion': '2024-11-05',
                        'capabilities': {'tools': {}},
                        'serverInfo': {'name': 'social-media-mcp', 'version': '1.0.0'}
                    }
                }
            
            else:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {'code': -32601, 'message': f'Method not found: {method}'}
                }
                
        except Exception as e:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {'code': -32603, 'message': str(e)}
            }
    
    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool by name."""
        tools_map = {
            'create_facebook_post': lambda args: create_facebook_post(
                content=args.get('content', ''),
                image_path=args.get('image_path'),
                scheduled_time=args.get('scheduled_time')
            ),
            'create_instagram_post': lambda args: create_instagram_post(
                content=args.get('content', ''),
                hashtags=args.get('hashtags'),
                image_path=args.get('image_path'),
                scheduled_time=args.get('scheduled_time')
            ),
            'create_twitter_tweet': lambda args: create_twitter_tweet(
                content=args.get('content', ''),
                scheduled_time=args.get('scheduled_time')
            ),
            'schedule_post': lambda args: schedule_post(
                post_id=args.get('post_id', ''),
                scheduled_time=args.get('scheduled_time', ''),
                platforms=args.get('platforms')
            ),
            'publish_post': lambda args: publish_post(
                post_id=args.get('post_id', '')
            ),
            'list_posts': lambda args: list_posts(
                status=args.get('status'),
                platform=args.get('platform'),
                limit=args.get('limit', 20)
            ),
            'cross_post': lambda args: cross_post(
                content=args.get('content', ''),
                platforms=args.get('platforms', []),
                hashtags=args.get('hashtags'),
                image_path=args.get('image_path'),
                scheduled_time=args.get('scheduled_time')
            ),
            'generate_content_summary': lambda args: generate_content_summary(
                source_content=args.get('source_content', ''),
                platform=args.get('platform', 'all'),
                tone=args.get('tone', 'professional')
            ),
            'cancel_post': lambda args: cancel_post(
                post_id=args.get('post_id', '')
            )
        }
        
        if name not in tools_map:
            return {'error': f'Unknown tool: {name}'}
        
        return tools_map[name](arguments)


def run_stdio_server():
    """Run the MCP server using stdio transport."""
    server = SocialMediaMCPServer()
    log_message("Social Media MCP Server started")
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = server.handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            log_message(f"Invalid JSON: {e}", "ERROR")
        except Exception as e:
            log_message(f"Error: {e}", "ERROR")


def run_cli():
    """Run in CLI mode for testing."""
    print("Social Media MCP Server - CLI Mode")
    print("\nAvailable tools:")
    print("  create_facebook_post    - Create Facebook post")
    print("  create_instagram_post   - Create Instagram post")
    print("  create_twitter_tweet    - Create Twitter tweet")
    print("  schedule_post           - Schedule post")
    print("  publish_post            - Publish immediately")
    print("  list_posts              - List all posts")
    print("  cross_post              - Post to multiple platforms")
    print("  generate_content_summary - Generate summaries")
    print("\nFor MCP integration, run without arguments for stdio mode.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        run_cli()
    else:
        run_stdio_server()
