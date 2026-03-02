#!/usr/bin/env python3
"""
Local Sync Client - Bidirectional sync between local and cloud vault
Excludes secrets (.env, tokens, credentials)
Supports rsync and git-based synchronization

Usage:
    python local-sync.py --setup      # Interactive setup
    python local-sync.py --sync       # Bidirectional sync
    python local-sync.py --push       # Push to cloud
    python local-sync.py --pull       # Pull from cloud
    python local-sync.py --status     # Show sync status
"""

import argparse
import json
import os
import subprocess
import sys
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# Files and patterns to exclude from sync
EXCLUDE_PATTERNS = [
    '.env',
    '.env.*',
    '!.env.example',
    '*.token',
    '*.key',
    '*.secret',
    '*credentials*',
    '*api_key*',
    'secrets/',
    'tokens/',
    'private/',
    '*.pem',
    '*.p12',
    '*.pfx',
    '__pycache__/',
    'node_modules/',
    '*.log',
    'logs/',
    '.git/',
    '.DS_Store',
    'Thumbs.db',
    '*.pyc',
    '*.pyo',
    'venv/',
    'ENV/',
    '.idea/',
    '.vscode/',
]


class SyncConfig:
    """Manages sync configuration"""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self.load()

    def load(self) -> dict:
        """Load configuration from file"""
        default_config = {
            'cloud_host': '',
            'cloud_user': 'oracle',
            'cloud_path': '/home/oracle/ai-employee',
            'local_path': str(Path.cwd()),
            'ssh_key': '',
            'exclude_patterns': EXCLUDE_PATTERNS.copy(),
            'sync_mode': 'bidirectional',  # push, pull, bidirectional
            'dry_run': False,
            'verbose': True,
            'last_sync': None,
            'sync_history': []
        }

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")

        return default_config

    def save(self):
        """Save configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def __getitem__(self, key):
        return self.config.get(key)

    def __setitem__(self, key, value):
        self.config[key] = value


class LocalSync:
    """Local sync client for AI Employee vault"""

    def __init__(self, config: SyncConfig):
        self.config = config
        self.local_path = Path(config['local_path'])
        self.cloud_host = config['cloud_host']
        self.cloud_user = config['cloud_user']
        self.cloud_path = config['cloud_path']
        self.ssh_key = config['ssh_key']
        self.exclude_patterns = config['exclude_patterns']

        # Build rsync exclude arguments
        self.rsync_excludes = []
        for pattern in self.exclude_patterns:
            self.rsync_excludes.extend(['--exclude', pattern])

        # SSH options
        self.ssh_opts = [
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
        ]
        if self.ssh_key:
            self.ssh_opts.extend(['-i', self.ssh_key])

    def check_connection(self) -> bool:
        """Check SSH connection to cloud VM"""
        if not self.cloud_host:
            print("❌ Cloud host not configured")
            return False

        try:
            cmd = ['ssh'] + self.ssh_opts + [
                f'{self.cloud_user}@{self.cloud_host}',
                'echo "Connection successful"'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                print(f"✅ Connected to {self.cloud_user}@{self.cloud_host}")
                return True
            else:
                print(f"❌ Connection failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Connection timeout")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    def get_local_files(self) -> Dict[str, str]:
        """Get hash of all local files (excluding patterns)"""
        files = {}

        for root, dirs, filenames in os.walk(self.local_path):
            # Filter directories
            dirs[:] = [d for d in dirs if f'{d}/' not in self.exclude_patterns]

            for filename in filenames:
                # Skip excluded patterns
                if any(pattern.replace('*', '') in filename for pattern in self.exclude_patterns if '*' in pattern):
                    continue
                if filename in self.exclude_patterns:
                    continue

                filepath = Path(root) / filename
                rel_path = str(filepath.relative_to(self.local_path))

                # Skip if in exclude list
                if any(rel_path.startswith(p.replace('*', '')) for p in self.exclude_patterns if '*' in p):
                    continue

                try:
                    # Calculate file hash
                    file_hash = hashlib.md5(filepath.read_bytes()).hexdigest()
                    files[rel_path] = file_hash
                except Exception as e:
                    continue

        return files

    def get_cloud_files(self) -> Dict[str, str]:
        """Get hash of all files on cloud VM"""
        if not self.check_connection():
            return {}

        try:
            # Get file list with hashes from cloud
            cmd = ['ssh'] + self.ssh_opts + [
                f'{self.cloud_user}@{self.cloud_host}',
                f'cd {self.cloud_path} && find . -type f -exec md5sum {{}} \\; 2>/dev/null'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                print(f"Error getting cloud files: {result.stderr}")
                return {}

            files = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        file_hash = parts[0]
                        file_path = parts[1].replace('./', '', 1)
                        files[file_path] = file_hash

            return files

        except Exception as e:
            print(f"Error getting cloud files: {e}")
            return {}

    def push_to_cloud(self, dry_run: bool = False) -> Tuple[int, int]:
        """Push local changes to cloud"""
        print("\n📤 Pushing changes to cloud...\n")

        if not self.check_connection():
            return 0, 0

        # Build rsync command
        cmd = [
            'rsync', '-avz', '--delete',
            '-e', f'ssh {" ".join(self.ssh_opts)}'
        ] + self.rsync_excludes

        if dry_run:
            cmd.append('--dry-run')

        # Add source and destination
        src = str(self.local_path) + '/'
        dest = f'{self.cloud_user}@{self.cloud_host}:{self.cloud_path}/'

        cmd.extend([src, dest])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # Parse rsync output
                lines = [l for l in result.stdout.split('\n') if l and not l.startswith('sending')]
                pushed = len([l for l in lines if 'sending' in l.lower() or l.startswith('.')])

                print(f"\n✅ Push complete")
                print(f"   Files synced: {pushed}")

                return pushed, 0
            else:
                print(f"❌ Push failed: {result.stderr}")
                return 0, 1

        except subprocess.TimeoutExpired:
            print("❌ Push timed out")
            return 0, 1
        except Exception as e:
            print(f"❌ Push error: {e}")
            return 0, 1

    def pull_from_cloud(self, dry_run: bool = False) -> Tuple[int, int]:
        """Pull changes from cloud"""
        print("\n📥 Pulling changes from cloud...\n")

        if not self.check_connection():
            return 0, 0

        # Build rsync command
        cmd = [
            'rsync', '-avz',
            '-e', f'ssh {" ".join(self.ssh_opts)}'
        ] + self.rsync_excludes

        if dry_run:
            cmd.append('--dry-run')

        # Add source and destination
        src = f'{self.cloud_user}@{self.cloud_host}:{self.cloud_path}/'
        dest = str(self.local_path) + '/'

        cmd.extend([src, dest])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # Parse rsync output
                lines = [l for l in result.stdout.split('\n') if l and not l.startswith('receiving')]
                pulled = len([l for l in lines if 'receiving' in l.lower() or l.startswith('.')])

                print(f"\n✅ Pull complete")
                print(f"   Files synced: {pulled}")

                return pulled, 0
            else:
                print(f"❌ Pull failed: {result.stderr}")
                return 0, 1

        except subprocess.TimeoutExpired:
            print("❌ Pull timed out")
            return 0, 1
        except Exception as e:
            print(f"❌ Pull error: {e}")
            return 0, 1

    def sync_bidirectional(self, dry_run: bool = False) -> Dict:
        """Perform bidirectional sync"""
        print("\n🔄 Starting bidirectional sync...\n")

        # Get file states
        print("Analyzing local files...")
        local_files = self.get_local_files()

        print("Analyzing cloud files...")
        cloud_files = self.get_cloud_files()

        # Compare
        local_only = set(local_files.keys()) - set(cloud_files.keys())
        cloud_only = set(cloud_files.keys()) - set(local_files.keys())
        common = set(local_files.keys()) & set(cloud_files.keys())

        # Find modified files
        modified = []
        for f in common:
            if local_files[f] != cloud_files[f]:
                modified.append(f)

        print(f"\n📊 Sync Analysis:")
        print(f"   Local only: {len(local_only)} files")
        print(f"   Cloud only: {len(cloud_only)} files")
        print(f"   Modified: {len(modified)} files")

        # Push new local files
        if local_only:
            print(f"\n📤 Pushing {len(local_only)} new local file(s)...")
            for f in list(local_only)[:10]:  # Show first 10
                print(f"   + {f}")
            if len(local_only) > 10:
                print(f"   ... and {len(local_only) - 10} more")

            self.push_to_cloud(dry_run)

        # Pull new cloud files
        if cloud_only:
            print(f"\n📥 Pulling {len(cloud_only)} new cloud file(s)...")
            for f in list(cloud_only)[:10]:
                print(f"   + {f}")
            if len(cloud_only) > 10:
                print(f"   ... and {len(cloud_only) - 10} more")

            self.pull_from_cloud(dry_run)

        # Handle modified files (prefer local version)
        if modified:
            print(f"\n⚠️  {len(modified)} file(s) modified in both locations")
            print("   Using local version (conflict resolution)")
            for f in modified[:10]:
                print(f"   ~ {f}")
            if len(modified) > 10:
                print(f"   ... and {len(modified) - 10} more")

            self.push_to_cloud(dry_run)

        # Update sync history
        self.config['last_sync'] = datetime.now().isoformat()
        self.config['sync_history'].append({
            'timestamp': datetime.now().isoformat(),
            'local_only': len(local_only),
            'cloud_only': len(cloud_only),
            'modified': len(modified)
        })

        # Keep last 10 syncs
        if len(self.config['sync_history']) > 10:
            self.config['sync_history'] = self.config['sync_history'][-10:]

        self.config.save()

        print("\n✅ Bidirectional sync complete")

        return {
            'local_only': len(local_only),
            'cloud_only': len(cloud_only),
            'modified': len(modified)
        }

    def show_status(self):
        """Show sync status"""
        print("\n📊 Local Sync Status\n")
        print("=" * 50)

        print(f"\n📍 Local Path: {self.local_path}")
        print(f"☁️  Cloud: {self.cloud_user}@{self.cloud_host}:{self.cloud_path}")
        print(f"🔑 SSH Key: {self.ssh_key or 'Not configured'}")

        # Connection status
        connected = self.check_connection()
        print(f"\n📡 Connection: {'✅ Connected' if connected else '❌ Disconnected'}")

        # Last sync
        last_sync = self.config['last_sync']
        if last_sync:
            print(f"🕐 Last Sync: {last_sync}")
        else:
            print("🕐 Last Sync: Never")

        # Sync history
        history = self.config['sync_history'][-5:]
        if history:
            print("\n📜 Recent Sync History:")
            for entry in history:
                ts = entry['timestamp'][:19]  # Remove microseconds
                total = entry['local_only'] + entry['cloud_only'] + entry['modified']
                print(f"   {ts}: {total} files synced")

        # Local file count
        local_files = self.get_local_files()
        print(f"\n📁 Local Files: {len(local_files)} (excluding secrets)")


def interactive_setup(config: SyncConfig):
    """Interactive setup wizard"""
    print("\n🔧 Local Sync Setup Wizard\n")
    print("=" * 50)

    print("\n📍 Local Configuration")
    print(f"   Local path: {config['local_path']}")
    change = input("   Change local path? (y/N): ").strip().lower()
    if change == 'y':
        new_path = input("   New path: ").strip()
        if os.path.isdir(new_path):
            config['local_path'] = new_path

    print("\n☁️  Cloud Configuration")
    config['cloud_host'] = input(f"   Cloud host/IP [{config['cloud_host']}]: ").strip() or config['cloud_host']
    config['cloud_user'] = input(f"   Cloud user [{config['cloud_user']}]: ").strip() or config['cloud_user']
    config['cloud_path'] = input(f"   Cloud path [{config['cloud_path']}]: ").strip() or config['cloud_path']

    print("\n🔑 SSH Configuration")
    config['ssh_key'] = input(f"   SSH key path [{config['ssh_key'] or 'default'}]: ").strip() or config['ssh_key']

    print("\n🔄 Sync Mode")
    print("   1. Bidirectional (default)")
    print("   2. Push only (local → cloud)")
    print("   3. Pull only (cloud → local)")
    mode = input("   Select mode [1]: ").strip() or '1'
    mode_map = {'1': 'bidirectional', '2': 'push', '3': 'pull'}
    config['sync_mode'] = mode_map.get(mode, 'bidirectional')

    # Save configuration
    config.save()

    print("\n✅ Configuration saved!")
    print(f"   Config file: {config.config_path}")


def main():
    parser = argparse.ArgumentParser(description='Local Sync Client for AI Employee Vault')
    parser.add_argument('--setup', action='store_true', help='Interactive setup')
    parser.add_argument('--sync', action='store_true', help='Bidirectional sync')
    parser.add_argument('--push', action='store_true', help='Push to cloud')
    parser.add_argument('--pull', action='store_true', help='Pull from cloud')
    parser.add_argument('--status', action='store_true', help='Show sync status')
    parser.add_argument('--check', action='store_true', help='Check connection')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run (no changes)')
    parser.add_argument('--config', '-c', type=str, help='Config file path')

    args = parser.parse_args()

    # Determine config path
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = Path(__file__).parent / 'config' / 'local-sync.json'

    # Load configuration
    config = SyncConfig(config_path)

    # Handle setup
    if args.setup:
        interactive_setup(config)
        return 0

    # Create sync client
    sync = LocalSync(config)

    # Handle commands
    if args.check:
        success = sync.check_connection()
        return 0 if success else 1

    if args.status:
        sync.show_status()
        return 0

    if args.sync:
        result = sync.sync_bidirectional(dry_run=args.dry_run)
        return 0

    if args.push:
        pushed, errors = sync.push_to_cloud(dry_run=args.dry_run)
        return 0 if errors == 0 else 1

    if args.pull:
        pulled, errors = sync.pull_from_cloud(dry_run=args.dry_run)
        return 0 if errors == 0 else 1

    # Default: show status
    sync.show_status()
    print("\n💡 Usage:")
    print("   python local-sync.py --setup    # First-time setup")
    print("   python local-sync.py --sync     # Bidirectional sync")
    print("   python local-sync.py --push     # Push to cloud")
    print("   python local-sync.py --pull     # Pull from cloud")
    print("   python local-sync.py --status   # Show status")

    return 0


if __name__ == '__main__':
    main()
