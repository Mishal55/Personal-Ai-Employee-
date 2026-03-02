#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Human-in-the-Loop Approval Workflow - Silver Tier Feature

Manages the approval workflow between Pending_Approval, Approved, and Rejected folders.
Provides CLI and API for reviewing and approving/rejecting pending items.

Usage:
    python approval_workflow.py --list              # List pending approvals
    python approval_workflow.py --show <file>       # Show details of a pending item
    python approval_workflow.py --approve <file>    # Approve a pending item
    python approval_workflow.py --reject <file>     # Reject a pending item
    python approval_workflow.py --batch             # Process all pending (interactive)
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


# Configuration
VAULT_PATH = Path(os.environ.get('AI_VAULT_PATH', r'D:\Personal Ai Employee\AI_Employee_Vault'))
PENDING_PATH = VAULT_PATH / 'Pending_Approval'
APPROVED_PATH = VAULT_PATH / 'Approved'
REJECTED_PATH = VAULT_PATH / 'Rejected'
DONE_PATH = VAULT_PATH / 'Done'
LOG_FILE = VAULT_PATH / 'Logs' / 'approval_workflow.log'
APPROVAL_LOG = VAULT_PATH / 'Logs' / 'approvals.jsonl'

# Ensure directories exist
for path in [PENDING_PATH, APPROVED_PATH, REJECTED_PATH, LOG_FILE.parent]:
    path.mkdir(parents=True, exist_ok=True)


def log_message(message: str, level: str = "INFO"):
    """Log a message to the log file."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    print(log_entry.strip())


def log_approval(action: str, file_name: str, details: dict):
    """Log approval action to JSONL file for audit trail."""
    entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'file': file_name,
        **details
    }
    with open(APPROVAL_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')


def extract_frontmatter(content: str) -> dict:
    """Extract YAML-like frontmatter from markdown content."""
    frontmatter = {}
    fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        fm_content = fm_match.group(1)
        for line in fm_content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()
    return frontmatter


def get_pending_items() -> List[Path]:
    """Get all pending approval items."""
    return sorted(PENDING_PATH.glob('*.md'))


def get_item_details(file_path: Path) -> dict:
    """Get detailed information about a pending item."""
    if not file_path.exists():
        return {'error': f'File not found: {file_path.name}'}
    
    content = file_path.read_text(encoding='utf-8')
    frontmatter = extract_frontmatter(content)
    
    # Determine item type from filename prefix
    item_type = 'unknown'
    if file_path.name.startswith('APPROVAL_'):
        item_type = 'approval'
    elif file_path.name.startswith('PLAN_'):
        item_type = 'plan'
    elif file_path.name.startswith('EMAIL_'):
        item_type = 'email'
    elif file_path.name.startswith('WHATSAPP_'):
        item_type = 'whatsapp'
    elif file_path.name.startswith('LINKEDIN_'):
        item_type = 'linkedin'
    elif file_path.name.startswith('PAYMENT_'):
        item_type = 'payment'
    
    # Extract main content (after frontmatter)
    main_content = content
    fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        main_content = content[fm_match.end():].strip()
    
    # Extract checkboxes status
    checked = len(re.findall(r'^- \[x\]', content, re.MULTILINE))
    unchecked = len(re.findall(r'^- \[ \]', content, re.MULTILINE))
    
    return {
        'file': str(file_path),
        'filename': file_path.name,
        'type': item_type,
        'status': frontmatter.get('status', 'pending_approval'),
        'created_at': frontmatter.get('created_at', 'Unknown'),
        'source': frontmatter.get('source', frontmatter.get('source_file', 'Unknown')),
        'priority': frontmatter.get('priority', 'normal'),
        'estimated_duration': frontmatter.get('estimated_duration_minutes', 'N/A'),
        'total_actions': frontmatter.get('total_actions', checked + unchecked),
        'progress': f"{checked}/{checked + unchecked}",
        'content': main_content,
        'frontmatter': frontmatter
    }


def list_pending(verbose: bool = False):
    """List all pending approval items."""
    log_message("Listing pending approvals...")
    
    pending = get_pending_items()
    
    if not pending:
        print("\n✅ No pending approvals!")
        print("All items have been processed.")
        return
    
    print(f"\n{'='*70}")
    print(f"PENDING APPROVALS ({len(pending)} items)")
    print(f"{'='*70}\n")
    
    for i, item_path in enumerate(pending, 1):
        details = get_item_details(item_path)
        
        # Color-code by type
        type_icons = {
            'approval': '📋',
            'plan': '📝',
            'email': '📧',
            'whatsapp': '💬',
            'linkedin': '💼',
            'payment': '💰',
            'unknown': '📄'
        }
        
        icon = type_icons.get(details['type'], '📄')
        
        print(f"{i}. {icon} {details['filename']}")
        print(f"   Type: {details['type']} | Priority: {details['priority']} | Progress: {details['progress']}")
        print(f"   Created: {details['created_at']}")
        
        if verbose:
            # Show first few lines of content
            content_preview = details['content'][:200].replace('\n', ' ')
            print(f"   Preview: {content_preview}...")
        
        print()
    
    print(f"{'='*70}")
    print(f"Use '--show <filename>' to view details")
    print(f"Use '--approve <filename>' to approve")
    print(f"Use '--reject <filename>' to reject with reason")


def show_item(filename: str):
    """Show detailed information about a specific item."""
    # Search in pending folder
    file_path = PENDING_PATH / filename
    if not file_path.exists():
        # Try without extension
        file_path = PENDING_PATH / f"{filename}.md"
    
    if not file_path.exists():
        print(f"❌ File not found: {filename}")
        return
    
    details = get_item_details(file_path)
    
    print(f"\n{'='*70}")
    print(f"FILE: {details['filename']}")
    print(f"{'='*70}\n")
    
    print(f"Type: {details['type']}")
    print(f"Status: {details['status']}")
    print(f"Priority: {details['priority']}")
    print(f"Created: {details['created_at']}")
    print(f"Progress: {details['progress']}")
    print()
    
    print("-"*70)
    print("CONTENT:")
    print("-"*70)
    print(details['content'])
    print()


def approve_item(filename: str, notes: str = "") -> bool:
    """Approve a pending item and move to Approved folder."""
    file_path = PENDING_PATH / filename
    if not file_path.exists():
        file_path = PENDING_PATH / f"{filename}.md"
    
    if not file_path.exists():
        print(f"❌ File not found: {filename}")
        return False
    
    details = get_item_details(file_path)
    content = file_path.read_text(encoding='utf-8')
    
    # Update frontmatter
    content = re.sub(r'^status: .+$', 'status: approved', content, flags=re.MULTILINE)
    
    # Add approval timestamp and notes
    approval_section = f"""
---
## Approval Information

**Approved At:** {datetime.now().isoformat()}
**Approved By:** Human Reviewer
**Notes:** {notes if notes else 'No notes provided'}

"""
    
    # Find the end of frontmatter and insert approval info
    fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        insert_pos = fm_match.end()
        content = content[:insert_pos] + f"\n\napproved_at: {datetime.now().isoformat()}\napproved_by: human_reviewer" + content[insert_pos:]
    
    # Determine destination filename
    new_filename = file_path.name
    if not new_filename.startswith('APPROVED_'):
        new_filename = f"APPROVED_{new_filename}"
    
    # Move to Approved folder
    dest_path = APPROVED_PATH / new_filename
    dest_path.write_text(content, encoding='utf-8')
    file_path.unlink()
    
    log_message(f"Approved: {filename} → {new_filename}")
    log_approval('approve', filename, {'notes': notes, 'destination': str(dest_path)})
    
    print(f"✅ Approved: {filename}")
    print(f"   Moved to: {dest_path}")
    
    return True


def reject_item(filename: str, reason: str = "") -> bool:
    """Reject a pending item and move to Rejected folder."""
    file_path = PENDING_PATH / filename
    if not file_path.exists():
        file_path = PENDING_PATH / f"{filename}.md"
    
    if not file_path.exists():
        print(f"❌ File not found: {filename}")
        return False
    
    details = get_item_details(file_path)
    content = file_path.read_text(encoding='utf-8')
    
    # Update frontmatter
    content = re.sub(r'^status: .+$', 'status: rejected', content, flags=re.MULTILINE)
    
    # Add rejection info
    content = re.sub(
        r'^---\n(.*?)\n---',
        f'---\n\\1\nrejected_at: {datetime.now().isoformat()}\nrejected_by: human_reviewer\nrejection_reason: {reason}',
        content,
        flags=re.DOTALL
    )
    
    # Add rejection section to content
    rejection_section = f"""
---

## Rejection Information

**Rejected At:** {datetime.now().isoformat()}
**Rejected By:** Human Reviewer
**Reason:** {reason if reason else 'No reason provided'}

"""
    content += rejection_section
    
    # Determine destination filename
    new_filename = file_path.name
    if not new_filename.startswith('REJECTED_'):
        new_filename = f"REJECTED_{new_filename}"
    
    # Move to Rejected folder
    dest_path = REJECTED_PATH / new_filename
    dest_path.write_text(content, encoding='utf-8')
    file_path.unlink()
    
    log_message(f"Rejected: {filename} - {reason}")
    log_approval('reject', filename, {'reason': reason, 'destination': str(dest_path)})
    
    print(f"❌ Rejected: {filename}")
    print(f"   Reason: {reason if reason else 'Not specified'}")
    print(f"   Moved to: {dest_path}")
    
    return True


def batch_process():
    """Interactive batch processing of all pending items."""
    pending = get_pending_items()
    
    if not pending:
        print("\n✅ No pending items to process!")
        return
    
    print(f"\n📋 Batch Processing Mode ({len(pending)} items)")
    print("="*70)
    
    approved_count = 0
    rejected_count = 0
    
    for item_path in pending:
        details = get_item_details(item_path)
        
        print(f"\n{'-'*70}")
        print(f"File: {details['filename']}")
        print(f"Type: {details['type']} | Priority: {details['priority']}")
        print(f"Progress: {details['progress']}")
        print()
        
        # Show content preview
        preview = details['content'][:500].replace('\n', ' ')
        print(f"Preview: {preview}...")
        print()
        
        while True:
            choice = input("[A]pprove / [R]eject / [S]kip / [Q]uit: ").strip().lower()
            
            if choice == 'a':
                notes = input("Approval notes (optional): ").strip()
                if approve_item(item_path.name, notes):
                    approved_count += 1
                break
            elif choice == 'r':
                reason = input("Rejection reason (required): ").strip()
                if not reason:
                    reason = "Not specified"
                if reject_item(item_path.name, reason):
                    rejected_count += 1
                break
            elif choice == 's':
                print("⏭️  Skipped")
                break
            elif choice == 'q':
                print(f"\n🛑 Batch processing stopped")
                print(f"Approved: {approved_count}, Rejected: {rejected_count}, Remaining: {len(get_pending_items())}")
                return
            else:
                print("Invalid choice. Please enter A, R, S, or Q.")
    
    print(f"\n{'='*70}")
    print(f"✅ Batch Complete!")
    print(f"   Approved: {approved_count}")
    print(f"   Rejected: {rejected_count}")
    print(f"   Remaining: {len(get_pending_items())}")


def show_approval_log(limit: int = 20):
    """Show recent approval log entries."""
    if not APPROVAL_LOG.exists():
        print("No approval log entries found.")
        return
    
    entries = []
    with open(APPROVAL_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    
    # Show most recent first
    entries = sorted(entries, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]
    
    print(f"\n{'='*70}")
    print(f"APPROVAL LOG (Last {len(entries)} entries)")
    print(f"{'='*70}\n")
    
    for entry in entries:
        action_icon = "✅" if entry.get('action') == 'approve' else "❌"
        print(f"{action_icon} {entry.get('timestamp', 'Unknown')} - {entry.get('action', 'unknown').upper()}: {entry.get('file', 'Unknown')}")
        if entry.get('notes'):
            print(f"   Notes: {entry['notes']}")
        if entry.get('reason'):
            print(f"   Reason: {entry['reason']}")
        print()


def main():
    parser = argparse.ArgumentParser(description='HITL Approval Workflow for AI Employee')
    parser.add_argument('--list', '-l', action='store_true', help='List pending approvals')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show more details in list')
    parser.add_argument('--show', '-s', type=str, metavar='FILE', help='Show details of a specific item')
    parser.add_argument('--approve', '-a', type=str, metavar='FILE', help='Approve a pending item')
    parser.add_argument('--reject', '-r', type=str, metavar='FILE', help='Reject a pending item')
    parser.add_argument('--reason', type=str, default='', help='Reason for rejection')
    parser.add_argument('--notes', '-n', type=str, default='', help='Notes for approval')
    parser.add_argument('--batch', '-b', action='store_true', help='Interactive batch processing')
    parser.add_argument('--log', action='store_true', help='Show approval log')
    
    args = parser.parse_args()
    
    if args.list:
        list_pending(verbose=args.verbose)
    elif args.show:
        show_item(args.show)
    elif args.approve:
        approve_item(args.approve, notes=args.notes)
    elif args.reject:
        reject_item(args.reject, reason=args.reason)
    elif args.batch:
        batch_process()
    elif args.log:
        show_approval_log()
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python approval_workflow.py --list")
        print("  python approval_workflow.py --show APPROVAL_payment_2026-02-25.md")
        print("  python approval_workflow.py --approve APPROVAL_payment_2026-02-25.md --notes 'Verified against invoice'")
        print("  python approval_workflow.py --reject APPROVAL_email_2026-02-25.md --reason 'Content needs revision'")
        print("  python approval_workflow.py --batch")


if __name__ == '__main__':
    main()
