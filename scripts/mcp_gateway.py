#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified MCP Gateway - Gold Tier Feature

A single entry point that routes requests to multiple MCP servers.
This simplifies client connections when using multiple MCP servers.

Supported Servers:
- odoo_accounting: Odoo Community accounting integration
- social_media: Facebook, Instagram, Twitter posting
- linkedin: LinkedIn auto-posting

Usage:
    python mcp_gateway.py --servers odoo_accounting,social_media
    python mcp_gateway.py --list-servers
"""

import argparse
import json
import os
import subprocess
import sys
import threading
from typing import Dict, List, Optional


class MCPGateway:
    """
    Unified gateway for multiple MCP servers.
    
    Routes incoming requests to appropriate backend servers
    and aggregates responses.
    """
    
    def __init__(self, server_configs: List[dict]):
        self.servers = {}
        self.server_processes = {}
        self.request_id = 0
        
        for config in server_configs:
            self.register_server(config)
    
    def register_server(self, config: dict):
        """Register an MCP server with the gateway."""
        name = config.get('name')
        command = config.get('command')
        
        if not name or not command:
            print(f"Invalid server config: {config}")
            return
        
        self.servers[name] = {
            'command': command,
            'description': config.get('description', ''),
            'tools': [],
            'process': None,
            'thread': None
        }
        
        print(f"Registered server: {name}")
    
    def start_servers(self):
        """Start all registered MCP servers."""
        for name, server in self.servers.items():
            try:
                # Start the server process
                process = subprocess.Popen(
                    server['command'],
                    shell=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                server['process'] = process
                server['tools'] = self._get_server_tools(process)
                
                print(f"Started server: {name} ({len(server['tools'])} tools)")
                
            except Exception as e:
                print(f"Failed to start server {name}: {e}")
    
    def _get_server_tools(self, process: subprocess.Popen) -> List[dict]:
        """Get available tools from a server."""
        try:
            # Send tools/list request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()
            
            # Read response
            response_line = process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                result = response.get('result', {})
                tools = result.get('tools', [])
                return tools
        except:
            pass
        
        return []
    
    def handle_request(self, request: dict) -> dict:
        """Handle an incoming request."""
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id', self.request_id)
        self.request_id += 1
        
        if method == 'tools/list':
            # Aggregate tools from all servers
            all_tools = []
            for name, server in self.servers.items():
                for tool in server['tools']:
                    # Prefix tool name with server name
                    prefixed_tool = tool.copy()
                    prefixed_tool['name'] = f"{name}.{tool['name']}"
                    prefixed_tool['server'] = name
                    all_tools.append(prefixed_tool)
            
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {'tools': all_tools}
            }
        
        elif method == 'tools/call':
            tool_name = params.get('name', '')
            arguments = params.get('arguments', {})
            
            # Parse server.tool format
            if '.' in tool_name:
                server_name, actual_tool = tool_name.split('.', 1)
            else:
                # Try to find the tool in any server
                server_name = self._find_tool_server(tool_name)
                actual_tool = tool_name
            
            if server_name and server_name in self.servers:
                return self._forward_to_server(
                    server_name, actual_tool, arguments, request_id
                )
            else:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {'code': -32601, 'message': f'Tool not found: {tool_name}'}
                }
        
        elif method == 'initialize':
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'protocolVersion': '2024-11-05',
                    'capabilities': {'tools': {}},
                    'serverInfo': {
                        'name': 'mcp-gateway',
                        'version': '1.0.0',
                        'servers': list(self.servers.keys())
                    }
                }
            }
        
        else:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {'code': -32601, 'message': f'Method not found: {method}'}
            }
    
    def _find_tool_server(self, tool_name: str) -> Optional[str]:
        """Find which server provides a tool."""
        for name, server in self.servers.items():
            for tool in server['tools']:
                if tool['name'] == tool_name:
                    return name
        return None
    
    def _forward_to_server(self, server_name: str, tool_name: str, 
                           arguments: dict, request_id: int) -> dict:
        """Forward a tool call to a specific server."""
        server = self.servers.get(server_name)
        if not server or not server['process']:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {'code': -32603, 'message': f'Server not available: {server_name}'}
            }
        
        try:
            # Forward request
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            server['process'].stdin.write(json.dumps(request) + "\n")
            server['process'].stdin.flush()
            
            # Read response
            response_line = server['process'].stdout.readline()
            if response_line:
                return json.loads(response_line)
            
        except Exception as e:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {'code': -32603, 'message': str(e)}
            }
        
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {'code': -32603, 'message': 'No response from server'}
        }
    
    def stop_servers(self):
        """Stop all server processes."""
        for name, server in self.servers.items():
            if server['process']:
                try:
                    server['process'].terminate()
                    server['process'].wait(timeout=5)
                    print(f"Stopped server: {name}")
                except:
                    pass


def get_default_servers() -> List[dict]:
    """Get default server configurations."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mcp_dir = os.path.join(script_dir, '..', 'mcp-servers')
    
    return [
        {
            'name': 'odoo_accounting',
            'command': f'python "{mcp_dir}\\odoo_accounting_mcp.py"',
            'description': 'Odoo Community accounting integration'
        },
        {
            'name': 'social_media',
            'command': f'python "{mcp_dir}\\social_media_mcp.py"',
            'description': 'Facebook, Instagram, Twitter posting'
        },
        {
            'name': 'linkedin',
            'command': f'python "{script_dir}\\linkedin_mcp_server.py"',
            'description': 'LinkedIn auto-posting'
        }
    ]


def list_servers():
    """List available MCP servers."""
    servers = get_default_servers()
    
    print("\nAvailable MCP Servers:")
    print("="*60)
    
    for server in servers:
        print(f"\n📌 {server['name']}")
        print(f"   Description: {server['description']}")
        print(f"   Command: {server['command']}")


def run_gateway(server_names: Optional[List[str]] = None):
    """Run the MCP gateway."""
    all_servers = get_default_servers()
    
    if server_names:
        selected = [s for s in all_servers if s['name'] in server_names]
        if not selected:
            print(f"No servers found matching: {server_names}")
            return
        all_servers = selected
    
    print(f"\n🚀 Starting MCP Gateway with {len(all_servers)} servers...")
    
    gateway = MCPGateway(all_servers)
    gateway.start_servers()
    
    print("\n✅ Gateway ready. Processing requests...\n")
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                response = gateway.handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError as e:
                print(json.dumps({
                    'jsonrpc': '2.0',
                    'error': {'code': -32700, 'message': f'Parse error: {e}'}
                }), flush=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping gateway...")
    finally:
        gateway.stop_servers()
        print("✅ Gateway stopped")


def main():
    parser = argparse.ArgumentParser(description='Unified MCP Gateway (Gold Tier)')
    parser.add_argument('--servers', type=str, help='Comma-separated list of servers to load')
    parser.add_argument('--list-servers', action='store_true', help='List available servers')
    
    args = parser.parse_args()
    
    if args.list_servers:
        list_servers()
    elif args.servers:
        server_names = [s.strip() for s in args.servers.split(',')]
        run_gateway(server_names)
    else:
        run_gateway()


if __name__ == '__main__':
    main()
