#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinkedIn Auto-Posting MCP Server - Silver Tier Feature

This MCP server provides tools for automated LinkedIn posting.
It integrates with the AI Employee's approval workflow.

Tools provided:
- create_linkedin_post: Draft a new LinkedIn post
- schedule_linkedin_post: Schedule a post for publishing
- publish_linkedin_post: Publish an approved post
- list_scheduled_posts: List all scheduled posts
- cancel_scheduled_post: Cancel a scheduled post

Usage:
    python linkedin_mcp_server.py
    
Or as stdio MCP server:
    npx -y @modelcontextprotocol/server --command "python linkedin_mcp_server.py"
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import asyncio


# Configuration
VAULT_PATH = Path(os.environ.get('AI_VAULT_PATH', r'D:\Personal Ai Employee\AI_Employee_Vault'))
LINKEDIN_DRAFTS_PATH = VAULT_PATH / 'watchers' / 'linkedin' / 'drafts'
LINKEDIN_SCHEDULED_PATH = VAULT_PATH / 'watchers' / 'linkedin' / 'scheduled'
LINKEDIN_PUBLISHED_PATH = VAULT_PATH / 'watchers' / 'linkedin' / 'published'
LINKEDIN_STATE_FILE = VAULT_PATH / 'watchers' / 'linkedin' / 'state.json'
LOG_FILE = VAULT_PATH / 'Logs' / 'linkedin_mcp.log'

# Ensure directories exist
for path in [LINKEDIN_DRAFTS_PATH, LINKEDIN_SCHEDULED_PATH, LINKEDIN_PUBLISHED_PATH]:
    path.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log_message(message: str, level: str = "INFO"):
    """Log a message to the log file."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def load_state() -> dict:
    """Load the LinkedIn state from file."""
    if LINKEDIN_STATE_FILE.exists():
        with open(LINKEDIN_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"posts": [], "last_sync": None}


def save_state(state: dict):
    """Save the LinkedIn state to file."""
    with open(LINKEDIN_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)


def generate_post_id() -> str:
    """Generate a unique post ID."""
    return f"LI_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def create_draft(content: str, scheduled_time: Optional[str] = None, 
                 hashtags: Optional[list] = None, 
                 include_image: bool = False,
                 image_path: Optional[str] = None) -> dict:
    """Create a LinkedIn post draft."""
    post_id = generate_post_id()
    
    draft = {
        'id': post_id,
        'content': content,
        'hashtags': hashtags or [],
        'include_image': include_image,
        'image_path': image_path,
        'scheduled_time': scheduled_time,
        'status': 'draft',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    # Save draft file
    draft_file = LINKEDIN_DRAFTS_PATH / f"{post_id}.md"
    full_content = format_post_markdown(draft)
    
    with open(draft_file, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    # Update state
    state = load_state()
    state['posts'].append(draft)
    save_state(state)
    
    log_message(f"Created draft post: {post_id}")
    
    return {
        'id': post_id,
        'status': 'draft',
        'file': str(draft_file),
        'message': f"Draft created. Requires approval before scheduling/publishing."
    }


def format_post_markdown(post: dict) -> str:
    """Format a post as markdown for the vault."""
    hashtags_str = '\n'.join(f"- #{tag}" for tag in post.get('hashtags', []))
    
    return f"""---
id: {post['id']}
type: linkedin_post
status: {post['status']}
created_at: {post['created_at']}
updated_at: {post['updated_at']}
scheduled_time: {post.get('scheduled_time', 'Not scheduled')}
include_image: {post.get('include_image', False)}
---

# LinkedIn Post Draft

## Content

{post['content']}

## Hashtags

{hashtags_str if hashtags_str else '*No hashtags*'}

## Media

{'![Image](' + post['image_path'] + ')' if post.get('image_path') else '*No image attached*'}

---

## Approval Workflow

- [ ] Content reviewed for accuracy
- [ ] Tone matches brand voice
- [ ] Hashtags are relevant
- [ ] Image (if any) is appropriate
- [ ] Scheduled time is optimal

## Publishing Status

| Stage | Status | Timestamp |
|-------|--------|-----------|
| Draft Created | ✅ | {post['created_at']} |
| Approval Requested | {'⏳' if post['status'] == 'pending_approval' else '○'} | - |
| Approved | {'✅' if post['status'] == 'approved' else '○'} | - |
| Scheduled | {'✅' if post['status'] == 'scheduled' else '○'} | - |
| Published | {'✅' if post['status'] == 'published' else '○'} | - |

---

*Managed by AI Employee LinkedIn MCP Server (Silver Tier)*
"""


def move_to_approval(post_id: str) -> dict:
    """Move a draft to pending approval."""
    state = load_state()
    
    for post in state['posts']:
        if post['id'] == post_id:
            if post['status'] != 'draft':
                return {'error': f"Post is not in draft status: {post['status']}"}
            
            post['status'] = 'pending_approval'
            post['updated_at'] = datetime.now().isoformat()
            
            # Move file
            old_file = LINKEDIN_DRAFTS_PATH / f"{post_id}.md"
            new_file = VAULT_PATH / 'Pending_Approval' / f"APPROVAL_linkedin_{post_id}.md"
            
            if old_file.exists():
                content = old_file.read_text(encoding='utf-8')
                # Update status in content
                content = content.replace('status: draft', 'status: pending_approval')
                new_file.write_text(content, encoding='utf-8')
                old_file.unlink()
            
            save_state(state)
            log_message(f"Post {post_id} moved to pending approval")
            
            return {
                'id': post_id,
                'status': 'pending_approval',
                'file': str(new_file),
                'message': "Post moved to Pending_Approval folder for human review."
            }
    
    return {'error': f"Post not found: {post_id}"}


def approve_post(post_id: str) -> dict:
    """Approve a post for publishing."""
    state = load_state()
    
    for post in state['posts']:
        if post['id'] == post_id:
            if post['status'] != 'pending_approval':
                return {'error': f"Post is not pending approval: {post['status']}"}
            
            post['status'] = 'approved'
            post['updated_at'] = datetime.now().isoformat()
            
            # Move file
            old_file = VAULT_PATH / 'Pending_Approval' / f"APPROVAL_linkedin_{post_id}.md"
            new_file = VAULT_PATH / 'Approved' / f"LINKEDIN_{post_id}.md"
            
            if old_file.exists():
                content = old_file.read_text(encoding='utf-8')
                content = content.replace('status: pending_approval', 'status: approved')
                new_file.write_text(content, encoding='utf-8')
                old_file.unlink()
            
            save_state(state)
            log_message(f"Post {post_id} approved")
            
            return {
                'id': post_id,
                'status': 'approved',
                'file': str(new_file),
                'message': "Post approved and ready for scheduling/publishing."
            }
    
    return {'error': f"Post not found: {post_id}"}


def schedule_post(post_id: str, scheduled_time: str) -> dict:
    """Schedule an approved post for publishing."""
    state = load_state()
    
    for post in state['posts']:
        if post['id'] == post_id:
            if post['status'] != 'approved':
                return {'error': f"Post must be approved before scheduling: {post['status']}"}
            
            post['scheduled_time'] = scheduled_time
            post['status'] = 'scheduled'
            post['updated_at'] = datetime.now().isoformat()
            
            # Move file
            old_file = VAULT_PATH / 'Approved' / f"LINKEDIN_{post_id}.md"
            new_file = LINKEDIN_SCHEDULED_PATH / f"{post_id}.md"
            
            if old_file.exists():
                content = old_file.read_text(encoding='utf-8')
                content = content.replace('status: approved', 'status: scheduled')
                content = content.replace(f"scheduled_time: Not scheduled", f"scheduled_time: {scheduled_time}")
                new_file.write_text(content, encoding='utf-8')
                old_file.unlink()
            
            save_state(state)
            log_message(f"Post {post_id} scheduled for {scheduled_time}")
            
            return {
                'id': post_id,
                'status': 'scheduled',
                'scheduled_time': scheduled_time,
                'file': str(new_file),
                'message': f"Post scheduled for {scheduled_time}"
            }
    
    return {'error': f"Post not found: {post_id}"}


def publish_post(post_id: str) -> dict:
    """Publish a post to LinkedIn (simulated - requires actual LinkedIn API for production)."""
    state = load_state()
    
    for post in state['posts']:
        if post['id'] == post_id:
            if post['status'] not in ['approved', 'scheduled']:
                return {'error': f"Post must be approved or scheduled: {post['status']}"}
            
            # In production, this would call LinkedIn API
            # For now, we simulate the publish
            post['status'] = 'published'
            post['published_at'] = datetime.now().isoformat()
            post['updated_at'] = datetime.now().isoformat()
            
            # Move file
            old_file = LINKEDIN_SCHEDULED_PATH / f"{post_id}.md"
            if not old_file.exists():
                old_file = VAULT_PATH / 'Approved' / f"LINKEDIN_{post_id}.md"
            
            new_file = LINKEDIN_PUBLISHED_PATH / f"{post_id}.md"
            
            if old_file.exists():
                content = old_file.read_text(encoding='utf-8')
                content = content.replace(f"status: {post['status']}", 'status: published')
                new_file.write_text(content, encoding='utf-8')
                old_file.unlink()
            
            save_state(state)
            log_message(f"Post {post_id} published")
            
            return {
                'id': post_id,
                'status': 'published',
                'published_at': post['published_at'],
                'message': "Post published successfully (simulated)."
            }
    
    return {'error': f"Post not found: {post_id}"}


def list_posts(status: Optional[str] = None) -> list:
    """List posts, optionally filtered by status."""
    state = load_state()
    posts = state.get('posts', [])
    
    if status:
        posts = [p for p in posts if p['status'] == status]
    
    return [{
        'id': p['id'],
        'status': p['status'],
        'created_at': p['created_at'],
        'scheduled_time': p.get('scheduled_time'),
        'content_preview': p['content'][:100] + '...' if len(p['content']) > 100 else p['content']
    } for p in posts]


def cancel_scheduled_post(post_id: str) -> dict:
    """Cancel a scheduled post and return to draft status."""
    state = load_state()
    
    for post in state['posts']:
        if post['id'] == post_id:
            if post['status'] != 'scheduled':
                return {'error': f"Post is not scheduled: {post['status']}"}
            
            post['status'] = 'draft'
            post['scheduled_time'] = None
            post['updated_at'] = datetime.now().isoformat()
            
            # Move file back to drafts
            old_file = LINKEDIN_SCHEDULED_PATH / f"{post_id}.md"
            new_file = LINKEDIN_DRAFTS_PATH / f"{post_id}.md"
            
            if old_file.exists():
                content = old_file.read_text(encoding='utf-8')
                content = content.replace('status: scheduled', 'status: draft')
                content = content.replace(f"scheduled_time: {post.get('scheduled_time', 'Not scheduled')}", 'scheduled_time: Not scheduled')
                new_file.write_text(content, encoding='utf-8')
                old_file.unlink()
            
            save_state(state)
            log_message(f"Post {post_id} cancelled and returned to drafts")
            
            return {
                'id': post_id,
                'status': 'draft',
                'message': "Post cancelled and returned to drafts."
            }
    
    return {'error': f"Post not found: {post_id}"}


# MCP Server Protocol Implementation

class LinkedInMCPServer:
    """MCP Server for LinkedIn automation."""
    
    def __init__(self):
        self.tools = {
            'create_linkedin_post': {
                'description': 'Create a new LinkedIn post draft',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'content': {
                            'type': 'string',
                            'description': 'The main content of the LinkedIn post'
                        },
                        'hashtags': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'List of hashtags (without # symbol)'
                        },
                        'include_image': {
                            'type': 'boolean',
                            'description': 'Whether to include an image'
                        },
                        'image_path': {
                            'type': 'string',
                            'description': 'Path to the image file (if include_image is true)'
                        }
                    },
                    'required': ['content']
                }
            },
            'schedule_linkedin_post': {
                'description': 'Schedule an approved post for publishing',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_id': {
                            'type': 'string',
                            'description': 'The ID of the post to schedule'
                        },
                        'scheduled_time': {
                            'type': 'string',
                            'description': 'ISO 8601 datetime for scheduled publishing'
                        }
                    },
                    'required': ['post_id', 'scheduled_time']
                }
            },
            'publish_linkedin_post': {
                'description': 'Publish an approved or scheduled post to LinkedIn',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_id': {
                            'type': 'string',
                            'description': 'The ID of the post to publish'
                        }
                    },
                    'required': ['post_id']
                }
            },
            'list_linkedin_posts': {
                'description': 'List LinkedIn posts, optionally filtered by status',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'status': {
                            'type': 'string',
                            'enum': ['draft', 'pending_approval', 'approved', 'scheduled', 'published'],
                            'description': 'Filter by post status'
                        }
                    }
                }
            },
            'cancel_scheduled_post': {
                'description': 'Cancel a scheduled post and return to draft status',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_id': {
                            'type': 'string',
                            'description': 'The ID of the post to cancel'
                        }
                    },
                    'required': ['post_id']
                }
            },
            'request_linkedin_approval': {
                'description': 'Move a draft post to pending approval status',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'post_id': {
                            'type': 'string',
                            'description': 'The ID of the post to submit for approval'
                        }
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
                        'content': [{'type': 'text', 'text': json.dumps(result, indent=2)}]
                    }
                }
            
            elif method == 'initialize':
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'protocolVersion': '2024-11-05',
                        'capabilities': {'tools': {}},
                        'serverInfo': {'name': 'linkedin-mcp-server', 'version': '1.0.0'}
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
            'create_linkedin_post': lambda args: create_draft(
                content=args.get('content', ''),
                hashtags=args.get('hashtags'),
                include_image=args.get('include_image', False),
                image_path=args.get('image_path')
            ),
            'schedule_linkedin_post': lambda args: schedule_post(
                post_id=args.get('post_id', ''),
                scheduled_time=args.get('scheduled_time', '')
            ),
            'publish_linkedin_post': lambda args: publish_post(
                post_id=args.get('post_id', '')
            ),
            'list_linkedin_posts': lambda args: list_posts(
                status=args.get('status')
            ),
            'cancel_scheduled_post': lambda args: cancel_scheduled_post(
                post_id=args.get('post_id', '')
            ),
            'request_linkedin_approval': lambda args: move_to_approval(
                post_id=args.get('post_id', '')
            )
        }
        
        if name not in tools_map:
            return {'error': f'Unknown tool: {name}'}
        
        return tools_map[name](arguments)


def run_stdio_server():
    """Run the MCP server using stdio transport."""
    server = LinkedInMCPServer()
    log_message("LinkedIn MCP Server started (stdio mode)")
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = server.handle_request(request)
            print(json.dumps(response), flush=True)
            
            # Handle notifications (no response needed)
            if request.get('method') == 'notifications/initialized':
                log_message("MCP client initialized")
                
        except json.JSONDecodeError as e:
            log_message(f"Invalid JSON received: {e}", "ERROR")
        except Exception as e:
            log_message(f"Error processing request: {e}", "ERROR")


def run_cli():
    """Run in CLI mode for testing."""
    print("LinkedIn MCP Server - CLI Mode")
    print("Available commands:")
    print("  list                    - List all posts")
    print("  create <content>        - Create a new draft")
    print("  approve <post_id>       - Approve a post")
    print("  schedule <post_id> <time> - Schedule a post")
    print("  publish <post_id>       - Publish a post")
    print("  cancel <post_id>        - Cancel a scheduled post")
    print()
    print("For MCP integration, run without arguments for stdio mode.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        run_cli()
    else:
        run_stdio_server()
