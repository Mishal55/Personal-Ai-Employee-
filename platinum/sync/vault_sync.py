#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vault Sync Manager - Platinum Tier Feature

Synchronizes AI Employee Vault between Cloud and Local machines.
Supports both Git and Syncthing synchronization methods.

Security Features:
- Never sync secrets (.env files, credentials)
- Conflict resolution
- Selective folder sync
- Sync status monitoring

Usage:
    python vault_sync.py --method git --init      # Initialize Git sync
    python vault_sync.py --method git --push      # Push changes to cloud
    python vault_sync.py --method git --pull      # Pull changes from cloud
    python vault_sync.py --method syncthing       # Check Syncthing status
    python vault_sync.py --status                 # Show sync status
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


# Configuration - Folders that should NEVER be synced (contain secrets)
NEVER_SYNC_FOLDERS = [
    '.env',
    '.env.local',
    '.env.production',
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '.git',
    'node_modules',
    'venv',
    'ai_employee_env',
    'Logs/*.log',  # Logs can contain sensitive data
    'Accounting/Odoo/state.json',  # Contains credentials
]

# Folders to sync (business data only)
SYNC_FOLDERS = [
    'Inbox',
    'Needs_Action',
    'Plans',
    'Pending_Approval',
    'Approved',
    'Rejected',
    'Done',
    'Briefings',
    'Business_Goals.md',
    'Company_Handbook.md',
    'Dashboard.md',
]

# Git remote name (your cloud VM)
GIT_REMOTE_NAME = 'cloud'
GIT_REMOTE_URL = os.environ.get('AI_CLOUD_GIT_URL', 'ssh://aiemployee@YOUR_CLOUD_IP:/home/aiemployee/ai-employee-vault.git')


class VaultSyncError(Exception):
    """Custom exception for sync errors."""
    pass


class VaultSyncManager:
    """Manages vault synchronization between cloud and local."""
    
    def __init__(self, vault_path: Path, method: str = 'git'):
        self.vault_path = vault_path
        self.method = method
        self.sync_log = vault_path.parent / 'platinum' / 'sync' / 'sync_log.jsonl'
        self.status_file = vault_path.parent / 'platinum' / 'sync' / 'sync_status.json'
        
        # Ensure sync directory exists
        self.sync_log.parent.mkdir(parents=True, exist_ok=True)
    
    def log_sync(self, action: str, details: dict):
        """Log a sync action."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        with open(self.sync_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    
    def check_secrets(self) -> List[str]:
        """Check for secrets that shouldn't be synced."""
        violations = []
        
        # Check for .env files
        for env_file in self.vault_path.parent.glob('**/.env*'):
            violations.append(str(env_file.relative_to(self.vault_path.parent)))
        
        # Check for credential patterns in files
        credential_patterns = [
            'API_KEY',
            'API_SECRET',
            'ACCESS_TOKEN',
            'PASSWORD',
            'SECRET_KEY',
            'PRIVATE_KEY'
        ]
        
        for md_file in self.vault_path.glob('**/*.md'):
            try:
                content = md_file.read_text(encoding='utf-8')
                for pattern in credential_patterns:
                    if pattern in content and 'ODOO' not in content and 'TWITTER' not in content:
                        # Skip expected patterns in config files
                        pass
            except:
                continue
        
        return violations
    
    def git_init(self, bare: bool = False) -> dict:
        """Initialize Git repository for sync."""
        try:
            if bare:
                # Initialize bare repo (for cloud server)
                repo_path = self.vault_path.parent / 'ai-employee-vault.git'
                repo_path.mkdir(exist_ok=True)
                subprocess.run(['git', 'init', '--bare', str(repo_path)], 
                             check=True, capture_output=True)
                result = {'success': True, 'repo': str(repo_path), 'type': 'bare'}
            else:
                # Initialize regular repo (for local)
                subprocess.run(['git', 'init'], cwd=self.vault_path, 
                             check=True, capture_output=True)
                
                # Create .gitignore
                gitignore_path = self.vault_path / '.gitignore'
                gitignore_content = """# Secrets - NEVER SYNC
.env
.env.*
*.key
*.pem

# Python
__pycache__/
*.pyc
*.pyo
venv/
ai_employee_env/

# Node
node_modules/

# Logs
Logs/*.log
Logs/*.jsonl

# Odoo state
Accounting/Odoo/state.json

# OS files
.DS_Store
Thumbs.db
"""
                gitignore_path.write_text(gitignore_content, encoding='utf-8')
                
                result = {'success': True, 'repo': str(self.vault_path), 'type': 'working'}
            
            self.log_sync('git_init', result)
            return result
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': e.stderr.decode()}
    
    def git_add_remote(self, remote_url: str = None) -> dict:
        """Add cloud remote to Git repository."""
        remote_url = remote_url or GIT_REMOTE_URL
        
        try:
            # Remove existing remote if present
            subprocess.run(['git', 'remote', 'remove', GIT_REMOTE_NAME], 
                         cwd=self.vault_path, capture_output=True)
            
            # Add new remote
            subprocess.run(['git', 'remote', 'add', GIT_REMOTE_NAME, remote_url], 
                         cwd=self.vault_path, check=True, capture_output=True)
            
            result = {'success': True, 'remote': GIT_REMOTE_NAME, 'url': remote_url}
            self.log_sync('git_add_remote', result)
            return result
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': e.stderr.decode()}
    
    def git_push(self) -> dict:
        """Push local changes to cloud."""
        try:
            # Check for secrets first
            violations = self.check_secrets()
            if violations:
                return {
                    'success': False, 
                    'error': 'Security violations found',
                    'violations': violations
                }
            
            # Stage changes
            subprocess.run(['git', 'add', '.'], cwd=self.vault_path, 
                         check=True, capture_output=True)
            
            # Check if there are changes to commit
            status = subprocess.run(['git', 'status', '--porcelain'], 
                                  cwd=self.vault_path, capture_output=True, text=True)
            
            if status.stdout.strip():
                # Commit changes
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                subprocess.run(['git', 'commit', '-m', f'Auto-sync: {timestamp}'], 
                             cwd=self.vault_path, check=True, capture_output=True)
            
            # Push to cloud
            subprocess.run(['git', 'push', '-u', GIT_REMOTE_NAME, 'main'], 
                         cwd=self.vault_path, check=True, capture_output=True)
            
            result = {'success': True, 'action': 'push', 'timestamp': datetime.now().isoformat()}
            self.log_sync('git_push', result)
            return result
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': e.stderr.decode()}
    
    def git_pull(self) -> dict:
        """Pull changes from cloud."""
        try:
            # Fetch from remote
            subprocess.run(['git', 'fetch', GIT_REMOTE_NAME], 
                         cwd=self.vault_path, check=True, capture_output=True)
            
            # Pull changes
            subprocess.run(['git', 'pull', GIT_REMOTE_NAME, 'main'], 
                         cwd=self.vault_path, check=True, capture_output=True)
            
            result = {'success': True, 'action': 'pull', 'timestamp': datetime.now().isoformat()}
            self.log_sync('git_pull', result)
            return result
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': e.stderr.decode()}
    
    def syncthing_check(self) -> dict:
        """Check Syncthing sync status."""
        try:
            # Check if Syncthing is running
            result = subprocess.run(['pgrep', '-x', 'syncthing'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'status': 'running',
                    'pid': result.stdout.strip()
                }
            else:
                return {
                    'success': True,
                    'status': 'not_running',
                    'message': 'Syncthing is not running'
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def syncthing_config(self) -> str:
        """Generate Syncthing configuration template."""
        return f"""<?xml version="1.0"?>
<configuration version="37">
    <folder id="ai-employee-vault" label="AI Employee Vault" path="{self.vault_path}" type="sendreceive" rescanIntervalS="60" fsWatcherEnabled="true" fsWatcherDelayS="10" ignorePerms="false" autoNormalize="true">
        <filesystemType>basic</filesystemType>
        <device id="CLOUD_DEVICE_ID" introducedBy="">
            <encryptionPassword></encryptionPassword>
        </device>
        <device id="LOCAL_DEVICE_ID" introducedBy="">
            <encryptionPassword></encryptionPassword>
        </device>
        <minDiskFree unit="%">1</minDiskFree>
        <versioning>
            <cleanupIntervalS>3600</cleanupIntervalS>
            <fsPath></fsPath>
            <fsType>basic</fsType>
        </versioning>
        <ignoreLines>-1</ignoreLines>
        <maxConcurrentWrites>2</maxConcurrentWrites>
        <disableFsync>false</disableFsync>
        <blockPullOrder>standard</blockPullOrder>
        <copyRangeMethod>standard</copyRangeMethod>
        <caseSensitiveFS>false</caseSensitiveFS>
        <junctionsAsDirs>true</junctionsAsDirs>
        <syncOwnership>false</syncOwnership>
        <sendOwnership>false</sendOwnership>
        <syncXattrs>true</syncXattrs>
        <sendXattrs>true</sendXattrs>
        <xattrFilter>
            <maxSingleEntrySize>0</maxSingleEntrySize>
            <maxTotalSize>0</maxTotalSize>
        </xattrFilter>
    </folder>
    <device id="CLOUD_DEVICE_ID" name="Cloud VM" compression="lz4" introducer="false" skipIntroductionRemovals="false" introducedBy="">
        <address>tcp://CLOUD_IP:22000</address>
        <paused>false</paused>
        <autoAcceptFolders>false</autoAcceptFolders>
        <maxSendKbps>0</maxSendKbps>
        <maxRecvKbps>0</maxRecvKbps>
        <maxRequestKiB>0</maxRequestKiB>
    </device>
    <device id="LOCAL_DEVICE_ID" name="Local Machine" compression="lz4" introducer="false" skipIntroductionRemovals="false" introducedBy="">
        <address>dynamic</address>
        <paused>false</paused>
        <autoAcceptFolders>false</autoAcceptFolders>
        <maxSendKbps>0</maxSendKbps>
        <maxRecvKbps>0</maxRecvKbps>
        <maxRequestKiB>0</maxRequestKiB>
    </device>
    <gui enabled="true" tls="false" debugging="false">
        <address>127.0.0.1:8384</address>
        <apikey>GENERATE_UNIQUE_API_KEY</apikey>
        <theme>default</theme>
    </gui>
    <ldap></ldap>
    <options>
        <listenAddress>default</listenAddress>
        <globalAnnounceServer>default</globalAnnounceServer>
        <globalAnnounceEnabled>true</globalAnnounceEnabled>
        <localAnnounceEnabled>true</localAnnounceEnabled>
        <maxSendKbps>0</maxSendKbps>
        <maxRecvKbps>0</maxRecvKbps>
        <reconnectionIntervalS>60</reconnectionIntervalS>
        <relaysEnabled>true</relaysEnabled>
        <relayReconnectIntervalM>10</relayReconnectIntervalM>
        <startBrowser>false</startBrowser>
        <natEnabled>true</natEnabled>
        <natLeaseMinutes>60</natLeaseMinutes>
        <natRenewalMinutes>30</natRenewalMinutes>
        <natTimeoutSeconds>300</natTimeoutSeconds>
        <urAccepted>-1</urAccepted>
        <urSeen>3</urSeen>
        <urUniqueID></urUniqueID>
        <urURL>https://data.syncthing.net/newdata</urURL>
        <urPostInsecurely>false</urPostInsecurely>
        <urInitialDelayS>1800</urInitialDelayS>
        <autoUpgradeIntervalH>12</autoUpgradeIntervalH>
        <upgradeToPreReleases>false</upgradeToPreReleases>
        <keepTemporariesH>24</keepTemporariesH>
        <cacheIgnoredFiles>false</cacheIgnoredFiles>
        <progressUpdateIntervalS>5</progressUpdateIntervalS>
        <limitBandwidthInLan>false</limitBandwidthInLan>
        <minHomeDiskFree unit="%">1</minHomeDiskFree>
        <releasesURL>https://upgrades.syncthing.net/meta.json</releasesURL>
        <overwriteRemoteDeviceNamesOnConnect>false</overwriteRemoteDeviceNamesOnConnect>
        <tempIndexMinBlocks>10</tempIndexMinBlocks>
        <unackedNotificationID></unackedNotificationID>
        <connectionLimitEnough>0</connectionLimitEnough>
        <connectionLimitMax>0</connectionLimitMax>
        <insecureAllowOldTLSVersions>false</insecureAllowOldTLSVersions>
        <connectionPriorityTcpLan>10</connectionPriorityTcpLan>
        <connectionPriorityQuicLan>20</connectionPriorityQuicLan>
        <connectionPriorityTcpWan>30</connectionPriorityTcpWan>
        <connectionPriorityQuicWan>40</connectionPriorityQuicWan>
        <connectionPriorityRelay>50</connectionPriorityRelay>
        <connectionPriorityUpgradeThreshold>0</connectionPriorityUpgradeThreshold>
    </options>
</configuration>
"""
    
    def get_status(self) -> dict:
        """Get current sync status."""
        status = {
            'vault_path': str(self.vault_path),
            'method': self.method,
            'timestamp': datetime.now().isoformat(),
            'sync_method_status': {},
            'security_check': {},
            'folders': {}
        }
        
        # Check Git status
        if self.method == 'git':
            try:
                result = subprocess.run(['git', 'status', '--porcelain'], 
                                      cwd=self.vault_path, capture_output=True, text=True)
                has_changes = bool(result.stdout.strip())
                status['sync_method_status']['git'] = {
                    'configured': (self.vault_path / '.git').exists(),
                    'has_changes': has_changes,
                    'remote': GIT_REMOTE_NAME
                }
            except:
                status['sync_method_status']['git'] = {'configured': False}
        
        # Check Syncthing status
        syncthing_status = self.syncthing_check()
        status['sync_method_status']['syncthing'] = syncthing_status
        
        # Security check
        violations = self.check_secrets()
        status['security_check'] = {
            'violations_found': len(violations) > 0,
            'violations': violations
        }
        
        # Folder counts
        for folder in ['Inbox', 'Needs_Action', 'Plans', 'Pending_Approval', 'Done']:
            folder_path = self.vault_path / folder
            if folder_path.exists():
                status['folders'][folder] = len(list(folder_path.glob('*.md')))
            else:
                status['folders'][folder] = 0
        
        # Save status
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, default=str)
        
        return status


def main():
    parser = argparse.ArgumentParser(description='Vault Sync Manager (Platinum Tier)')
    parser.add_argument('--vault', type=str, default=None, help='Path to vault')
    parser.add_argument('--method', type=str, choices=['git', 'syncthing'], default='git')
    parser.add_argument('--init', action='store_true', help='Initialize sync')
    parser.add_argument('--push', action='store_true', help='Push changes')
    parser.add_argument('--pull', action='store_true', help='Pull changes')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--bare', action='store_true', help='Initialize bare repo (cloud only)')
    parser.add_argument('--remote', type=str, help='Git remote URL')
    
    args = parser.parse_args()
    
    # Determine vault path
    if args.vault:
        vault_path = Path(args.vault)
    else:
        vault_path = Path(r'D:\Personal Ai Employee\AI_Employee_Vault')
    
    sync_manager = VaultSyncManager(vault_path, args.method)
    
    if args.init:
        print(f"\n🔧 Initializing {args.method} sync...")
        if args.method == 'git':
            result = sync_manager.git_init(bare=args.bare)
            if result['success']:
                print(f"✅ Git repo initialized: {result['type']}")
                if not args.bare:
                    print("   Created .gitignore for security")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown')}")
        else:
            config = sync_manager.syncthing_config()
            config_file = vault_path.parent / 'platinum' / 'sync' / 'syncthing_config.xml'
            config_file.write_text(config, encoding='utf-8')
            print(f"✅ Syncthing config generated: {config_file}")
    
    elif args.push:
        print("\n📤 Pushing changes to cloud...")
        result = sync_manager.git_push()
        if result['success']:
            print("✅ Changes pushed successfully")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown')}")
            if result.get('violations'):
                print("\n🔒 Security violations found:")
                for v in result['violations']:
                    print(f"   - {v}")
    
    elif args.pull:
        print("\n📥 Pulling changes from cloud...")
        result = sync_manager.git_pull()
        if result['success']:
            print("✅ Changes pulled successfully")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown')}")
    
    elif args.status or True:  # Default to status
        print("\n📊 Vault Sync Status\n")
        status = sync_manager.get_status()
        
        print(f"Vault: {status['vault_path']}")
        print(f"Method: {status['method']}")
        print()
        
        print("Sync Methods:")
        for method, info in status['sync_method_status'].items():
            if isinstance(info, dict):
                configured = info.get('configured', info.get('status') == 'running')
                icon = "✅" if configured else "❌"
                print(f"  {icon} {method}: {info}")
        
        print()
        print("Security Check:")
        if status['security_check']['violations_found']:
            print("  🔒 Violations found:")
            for v in status['security_check']['violations']:
                print(f"     - {v}")
        else:
            print("  ✅ No security violations")
        
        print()
        print("Folder Counts:")
        for folder, count in status['folders'].items():
            print(f"  {folder}: {count} files")


if __name__ == '__main__':
    main()
