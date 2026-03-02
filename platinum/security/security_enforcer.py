#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Rules Enforcer - Platinum Tier Feature

Enforces security policies for AI Employee deployment:
- Secret detection and prevention
- File permission checks
- Access control enforcement
- Audit logging

Usage:
    python security_enforcer.py --scan          # Scan for violations
    python security_enforcer.py --fix           # Auto-fix issues
    python security_enforcer.py --audit         # Generate audit report
"""

import argparse
import json
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple


# Security patterns that indicate secrets
SECRET_PATTERNS = [
    (r'API_KEY\s*=\s*["\']?[A-Za-z0-9]{20,}', 'API Key'),
    (r'API_SECRET\s*=\s*["\']?[A-Za-z0-9]{20,}', 'API Secret'),
    (r'ACCESS_TOKEN\s*=\s*["\']?[A-Za-z0-9]{20,}', 'Access Token'),
    (r'PRIVATE_KEY\s*=\s*["\']?-----BEGIN', 'Private Key'),
    (r'PASSWORD\s*=\s*["\']?[^\s"\']{8,}', 'Password'),
    (r'SECRET_KEY\s*=\s*["\']?[A-Za-z0-9]{20,}', 'Secret Key'),
    (r'AWS_ACCESS_KEY_ID\s*=\s*[A-Z0-9]{20}', 'AWS Access Key'),
    (r'AWS_SECRET_ACCESS_KEY\s*=\s*[A-Za-z0-9/+=]{40}', 'AWS Secret Key'),
    (r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+', 'JWT Token'),
    (r'sk-[A-Za-z0-9]{48}', 'OpenAI API Key'),
]

# Files that should never be synced
NEVER_SYNC_FILES = [
    '.env',
    '.env.local',
    '.env.production',
    '.git/config',  # May contain credentials
    'credentials.json',
    'service_account.json',
    '*.key',
    '*.pem',
    '*.p12',
    '*.pfx',
]

# Required secure permissions (octal)
SECURE_PERMISSIONS = {
    '.env': 0o600,  # Owner read/write only
    '.env.*': 0o600,
    '*.key': 0o600,
    '*.pem': 0o600,
}


class SecurityViolation:
    """Represents a security violation."""
    
    def __init__(self, severity: str, category: str, description: str, 
                 file_path: str = None, fix_available: bool = False):
        self.severity = severity  # critical, high, medium, low
        self.category = category
        self.description = description
        self.file_path = file_path
        self.fix_available = fix_available
    
    def to_dict(self) -> dict:
        return {
            'severity': self.severity,
            'category': self.category,
            'description': self.description,
            'file_path': self.file_path,
            'fix_available': self.fix_available
        }


class SecurityEnforcer:
    """Enforces security policies for AI Employee."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.violations: List[SecurityViolation] = []
        self.audit_log = base_path.parent / 'platinum' / 'security' / 'audit_log.jsonl'
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
    
    def log_audit(self, action: str, details: dict):
        """Log an audit event."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        with open(self.audit_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    
    def scan_for_secrets(self) -> List[SecurityViolation]:
        """Scan files for exposed secrets."""
        violations = []
        
        # Files to scan
        files_to_scan = list(self.base_path.glob('**/*.md'))
        files_to_scan.extend(self.base_path.glob('**/*.py'))
        files_to_scan.extend(self.base_path.glob('**/*.json'))
        files_to_scan.extend(self.base_path.glob('**/*.txt'))
        files_to_scan.extend(self.base_path.glob('**/.env*'))
        
        for file_path in files_to_scan:
            if not file_path.is_file():
                continue
            
            # Skip audit log itself
            if file_path == self.audit_log:
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                
                for pattern, secret_type in SECRET_PATTERNS:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Check if it's in a safe context (example/documentation)
                        line_start = content.rfind('\n', 0, match.start()) + 1
                        line_end = content.find('\n', match.end())
                        line = content[line_start:line_end].lower()
                        
                        # Skip if it's clearly an example
                        if any(skip in line for skip in ['example', 'your_', 'xxx', 'change_me', 'placeholder']):
                            continue
                        
                        violations.append(SecurityViolation(
                            severity='critical',
                            category='exposed_secret',
                            description=f'{secret_type} detected in file',
                            file_path=str(file_path.relative_to(self.base_path)),
                            fix_available=True
                        ))
                        
            except Exception as e:
                continue
        
        return violations
    
    def check_unsafe_files(self) -> List[SecurityViolation]:
        """Check for files that shouldn't exist or be synced."""
        violations = []
        
        for pattern in NEVER_SYNC_FILES:
            if '*' in pattern:
                # Glob pattern
                for file_path in self.base_path.glob(f'**/{pattern}'):
                    if file_path.is_file():
                        violations.append(SecurityViolation(
                            severity='high',
                            category='unsafe_file',
                            description=f'File should not exist in vault: {pattern}',
                            file_path=str(file_path.relative_to(self.base_path)),
                            fix_available=True
                        ))
            else:
                # Exact match
                file_path = self.base_path / pattern
                if file_path.exists():
                    violations.append(SecurityViolation(
                        severity='high',
                        category='unsafe_file',
                        description=f'File should not exist in vault: {pattern}',
                        file_path=str(file_path.relative_to(self.base_path)),
                        fix_available=True
                    ))
        
        return violations
    
    def check_permissions(self) -> List[SecurityViolation]:
        """Check file permissions for security issues."""
        violations = []
        
        for file_path in self.base_path.glob('**/.env*'):
            if file_path.is_file():
                try:
                    mode = file_path.stat().st_mode & 0o777
                    if mode != 0o600:
                        violations.append(SecurityViolation(
                            severity='medium',
                            category='insecure_permissions',
                            description=f'.env file has insecure permissions: {oct(mode)}',
                            file_path=str(file_path.relative_to(self.base_path)),
                            fix_available=True
                        ))
                except:
                    continue
        
        return violations
    
    def check_git_config(self) -> List[SecurityViolation]:
        """Check Git configuration for credentials."""
        violations = []
        
        git_config = self.base_path / '.git' / 'config'
        if git_config.exists():
            try:
                content = git_config.read_text(encoding='utf-8')
                
                # Check for credentials in URL
                if re.search(r'://[^:]+:[^@]+@', content):
                    violations.append(SecurityViolation(
                        severity='critical',
                        category='git_credentials',
                        description='Git config contains embedded credentials',
                        file_path='.git/config',
                        fix_available=True
                    ))
            except:
                pass
        
        return violations
    
    def fix_violations(self, violations: List[SecurityViolation]) -> Dict[str, int]:
        """Attempt to fix security violations."""
        results = {
            'fixed': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for violation in violations:
            try:
                if violation.category == 'insecure_permissions':
                    # Fix permissions
                    file_path = self.base_path / violation.file_path
                    file_path.chmod(0o600)
                    results['fixed'] += 1
                    self.log_audit('fix_permissions', {
                        'file': violation.file_path,
                        'old_mode': 'insecure',
                        'new_mode': '0600'
                    })
                
                elif violation.category == 'unsafe_file':
                    # Move to quarantine
                    file_path = self.base_path / violation.file_path
                    quarantine_dir = self.base_path.parent / 'platinum' / 'security' / 'quarantine'
                    quarantine_dir.mkdir(parents=True, exist_ok=True)
                    
                    shutil.move(str(file_path), str(quarantine_dir / file_path.name))
                    results['fixed'] += 1
                    self.log_audit('quarantine_file', {
                        'file': violation.file_path,
                        'reason': 'unsafe_file'
                    })
                
                elif violation.category == 'exposed_secret':
                    # Can't auto-fix, needs manual review
                    results['skipped'] += 1
                
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                results['failed'] += 1
                self.log_audit('fix_failed', {
                    'violation': violation.to_dict(),
                    'error': str(e)
                })
        
        return results
    
    def generate_audit_report(self) -> str:
        """Generate a security audit report."""
        # Run all checks
        secret_violations = self.scan_for_secrets()
        file_violations = self.check_unsafe_files()
        permission_violations = self.check_permissions()
        git_violations = self.check_git_config()
        
        all_violations = secret_violations + file_violations + permission_violations + git_violations
        
        # Count by severity
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for v in all_violations:
            severity_counts[v.severity] = severity_counts.get(v.severity, 0) + 1
        
        # Generate report
        report = f"""# Security Audit Report

**Generated:** {datetime.now().isoformat()}
**Path:** {self.base_path}

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | {severity_counts['critical']} |
| 🟠 High | {severity_counts['high']} |
| 🟡 Medium | {severity_counts['medium']} |
| 🟢 Low | {severity_counts['low']} |

**Total Violations:** {len(all_violations)}

## Findings

"""
        
        if all_violations:
            # Group by category
            by_category = {}
            for v in all_violations:
                if v.category not in by_category:
                    by_category[v.category] = []
                by_category[v.category].append(v)
            
            for category, violations in by_category.items():
                report += f"\n### {category.replace('_', ' ').title()}\n\n"
                for v in violations:
                    fix_status = "🔧 Fix available" if v.fix_available else "⚠️ Manual review required"
                    report += f"- **[{v.severity.upper()}]** {v.description}\n"
                    report += f"  - File: `{v.file_path}`\n"
                    report += f"  - Status: {fix_status}\n\n"
        else:
            report += "\n✅ **No security violations found!**\n"
        
        report += f"""
## Recommendations

1. **Secrets Management**: Use environment variables or a secrets manager
2. **File Permissions**: Ensure .env files are 600 (owner read/write only)
3. **Git Configuration**: Use SSH keys instead of embedded credentials
4. **Regular Audits**: Run security scans weekly

---
*Generated by AI Employee Security Enforcer (Platinum Tier)*
"""
        
        return report
    
    def run_full_scan(self) -> Tuple[List[SecurityViolation], str]:
        """Run full security scan and return violations + report."""
        violations = (
            self.scan_for_secrets() +
            self.check_unsafe_files() +
            self.check_permissions() +
            self.check_git_config()
        )
        
        report = self.generate_audit_report()
        
        self.log_audit('full_scan', {
            'violations_found': len(violations),
            'by_severity': {
                'critical': sum(1 for v in violations if v.severity == 'critical'),
                'high': sum(1 for v in violations if v.severity == 'high'),
                'medium': sum(1 for v in violations if v.severity == 'medium'),
                'low': sum(1 for v in violations if v.severity == 'low')
            }
        })
        
        return violations, report


def main():
    parser = argparse.ArgumentParser(description='Security Enforcer (Platinum Tier)')
    parser.add_argument('--scan', action='store_true', help='Scan for violations')
    parser.add_argument('--fix', action='store_true', help='Auto-fix issues')
    parser.add_argument('--audit', action='store_true', help='Generate audit report')
    parser.add_argument('--path', type=str, default=None, help='Base path to scan')
    
    args = parser.parse_args()
    
    # Determine base path
    if args.path:
        base_path = Path(args.path)
    else:
        base_path = Path(r'D:\Personal Ai Employee\AI_Employee_Vault')
    
    enforcer = SecurityEnforcer(base_path)
    
    if args.scan:
        print("\n🔍 Scanning for security violations...\n")
        violations, _ = enforcer.run_full_scan()
        
        if violations:
            print(f"Found {len(violations)} violations:\n")
            for v in violations[:10]:  # Show first 10
                icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(v.severity, '⚪')
                print(f"  {icon} [{v.severity.upper()}] {v.description}")
                print(f"      File: {v.file_path}")
                print()
            if len(violations) > 10:
                print(f"... and {len(violations) - 10} more")
        else:
            print("✅ No security violations found!")
    
    elif args.fix:
        print("\n🔧 Fixing security issues...\n")
        violations, _ = enforcer.run_full_scan()
        
        if violations:
            results = enforcer.fix_violations(violations)
            print(f"Fixed: {results['fixed']}")
            print(f"Failed: {results['failed']}")
            print(f"Skipped (manual review): {results['skipped']}")
        else:
            print("✅ No issues to fix!")
    
    elif args.audit:
        print("\n📊 Generating security audit report...\n")
        _, report = enforcer.run_full_scan()
        
        # Save report
        report_file = base_path.parent / 'platinum' / 'security' / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_file.write_text(report, encoding='utf-8')
        
        print(report)
        print(f"\nReport saved to: {report_file}")
    
    else:
        # Default: show status
        print("\n🔒 Security Enforcer (Platinum Tier)")
        print("\nUsage:")
        print("  python security_enforcer.py --scan    # Scan for violations")
        print("  python security_enforcer.py --fix     # Auto-fix issues")
        print("  python security_enforcer.py --audit   # Generate report")


if __name__ == '__main__':
    import shutil  # Import here to avoid issues when used as module
    main()
