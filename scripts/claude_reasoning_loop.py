#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Reasoning Loop - Silver Tier Feature

Generates Plan.md files with checkboxes for task execution.
Implements a reasoning loop that:
1. Analyzes incoming tasks from Inbox/Needs_Action
2. Generates structured plans with checkboxes
3. Tracks progress and updates plans
4. Moves completed items to Done/

Usage:
    python claude_reasoning_loop.py --analyze     # Analyze inbox and create plans
    python claude_reasoning_loop.py --process     # Process pending plans
    python claude_reasoning_loop.py --status      # Show status of all plans
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


# Configuration
VAULT_PATH = Path(os.environ.get('AI_VAULT_PATH', r'D:\Personal Ai Employee\AI_Employee_Vault'))
INBOX_PATH = VAULT_PATH / 'Inbox'
NEEDS_ACTION_PATH = VAULT_PATH / 'Needs_Action'
PLANS_PATH = VAULT_PATH / 'Plans'
PENDING_APPROVAL_PATH = VAULT_PATH / 'Pending_Approval'
APPROVED_PATH = VAULT_PATH / 'Approved'
DONE_PATH = VAULT_PATH / 'Done'
LOG_FILE = VAULT_PATH / 'Logs' / 'reasoning_loop.log'
STATE_FILE = VAULT_PATH / 'Plans' / 'reasoning_state.json'

# Ensure directories exist
for path in [PLANS_PATH, LOG_FILE.parent]:
    path.mkdir(parents=True, exist_ok=True)


def log_message(message: str, level: str = "INFO"):
    """Log a message to the log file."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    print(log_entry.strip())


def load_state() -> dict:
    """Load the reasoning state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"processed_files": [], "active_plans": [], "last_run": None}


def save_state(state: dict):
    """Save the reasoning state to file."""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)


def extract_task_info(file_path: Path) -> dict:
    """Extract task information from an inbox/needs_action file."""
    content = file_path.read_text(encoding='utf-8')
    
    # Extract frontmatter
    frontmatter = {}
    fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        fm_content = fm_match.group(1)
        for line in fm_content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()
    
    # Extract main content
    main_content = content
    if fm_match:
        main_content = content[fm_match.end():].strip()
    
    # Determine task type and priority
    task_type = frontmatter.get('source', 'unknown').upper()
    priority = 'normal'
    
    if 'URGENT' in file_path.name or 'urgent' in content.lower():
        priority = 'urgent'
    elif 'HIGH' in file_path.name or 'high priority' in content.lower():
        priority = 'high'
    
    return {
        'file': str(file_path),
        'filename': file_path.name,
        'source': task_type,
        'priority': priority,
        'frontmatter': frontmatter,
        'content': main_content,
        'created_at': frontmatter.get('received_at', frontmatter.get('created_at', datetime.now().isoformat()))
    }


def generate_action_items(task_info: dict) -> List[dict]:
    """Generate action items based on task analysis."""
    content = task_info['content'].lower()
    source = task_info['source']
    action_items = []
    
    # Pattern-based action generation
    patterns = [
        (r'invoice', 'financial', [
            {'action': 'Review invoice details', 'type': 'review'},
            {'action': 'Verify against purchase order', 'type': 'verification'},
            {'action': 'Check budget allocation', 'type': 'verification'},
            {'action': 'Route for approval if > $100', 'type': 'approval'},
            {'action': 'Process payment', 'type': 'execution'},
            {'action': 'Archive to Accounting/', 'type': 'filing'}
        ]),
        (r'email|reply|respond', 'communication', [
            {'action': 'Analyze email intent', 'type': 'analysis'},
            {'action': 'Draft response', 'type': 'draft'},
            {'action': 'Review draft for tone and accuracy', 'type': 'review'},
            {'action': 'Submit for approval (if new contact)', 'type': 'approval'},
            {'action': 'Send email', 'type': 'execution'},
            {'action': 'Log communication', 'type': 'filing'}
        ]),
        (r'whatsapp|message', 'communication', [
            {'action': 'Categorize message intent', 'type': 'analysis'},
            {'action': 'Determine if response needed', 'type': 'analysis'},
            {'action': 'Draft response', 'type': 'draft'},
            {'action': 'Submit for approval', 'type': 'approval'},
            {'action': 'Send message', 'type': 'execution'}
        ]),
        (r'file|document|receipt', 'processing', [
            {'action': 'Identify document type', 'type': 'analysis'},
            {'action': 'Extract key information', 'type': 'extraction'},
            {'action': 'Categorize and tag', 'type': 'classification'},
            {'action': 'Store in appropriate folder', 'type': 'filing'},
            {'action': 'Update index/log', 'type': 'documentation'}
        ]),
        (r'payment|pay|transfer', 'financial', [
            {'action': 'Verify recipient details', 'type': 'verification'},
            {'action': 'Check if new recipient', 'type': 'verification'},
            {'action': 'Verify amount and purpose', 'type': 'verification'},
            {'action': 'Route for approval (all payments)', 'type': 'approval'},
            {'action': 'Execute payment', 'type': 'execution'},
            {'action': 'Record in accounting log', 'type': 'documentation'}
        ]),
        (r'schedule|meeting|appointment', 'scheduling', [
            {'action': 'Check calendar availability', 'type': 'verification'},
            {'action': 'Propose time slots', 'type': 'draft'},
            {'action': 'Confirm with participants', 'type': 'communication'},
            {'action': 'Create calendar entry', 'type': 'execution'},
            {'action': 'Send invitations', 'type': 'communication'}
        ]),
        (r'linkedin|post|social', 'marketing', [
            {'action': 'Review content guidelines', 'type': 'review'},
            {'action': 'Draft post content', 'type': 'draft'},
            {'action': 'Add relevant hashtags', 'type': 'enhancement'},
            {'action': 'Submit for approval', 'type': 'approval'},
            {'action': 'Schedule or publish', 'type': 'execution'}
        ])
    ]
    
    matched_category = 'general'
    matched_actions = []
    
    for pattern, category, actions in patterns:
        if re.search(pattern, content):
            matched_category = category
            matched_actions = actions
            break
    
    if not matched_actions:
        # Default actions for unknown tasks
        matched_actions = [
            {'action': 'Analyze task requirements', 'type': 'analysis'},
            {'action': 'Identify required resources', 'type': 'planning'},
            {'action': 'Create execution plan', 'type': 'planning'},
            {'action': 'Execute task', 'type': 'execution'},
            {'action': 'Verify completion', 'type': 'verification'}
        ]
    
    # Add HITL checkpoint based on Company Handbook rules
    if source in ['EMAIL', 'WHATSAPP']:
        matched_actions.append({'action': 'HITL: Verify communication appropriateness', 'type': 'approval'})
    
    if 'payment' in content and ('$500' in content or '$100' in content or 'new' in content):
        matched_actions.append({'action': 'HITL: Payment requires explicit approval', 'type': 'approval'})
    
    return [{
        'id': f"ACT_{i+1:03d}",
        'action': item['action'],
        'type': item['type'],
        'status': 'pending',
        'completed_at': None
    } for i, item in enumerate(matched_actions)]


def generate_plan_md(task_info: dict, action_items: List[dict]) -> str:
    """Generate a Plan.md file with checkboxes."""
    plan_id = f"PLAN_{task_info['filename'].replace('.md', '')}_{datetime.now().strftime('%Y%m%d')}"
    
    # Calculate estimated duration based on action count
    estimated_minutes = len(action_items) * 5
    
    action_items_md = '\n'.join([
        f"- [ ] **{item['id']}** [{item['type']}] {item['action']}"
        for item in action_items
    ])
    
    return f"""---
plan_id: {plan_id}
source_file: {task_info['filename']}
source_type: {task_info['source']}
priority: {task_info['priority']}
created_at: {datetime.now().isoformat()}
status: draft
estimated_duration_minutes: {estimated_minutes}
total_actions: {len(action_items)}
completed_actions: 0
---

# Task Plan: {task_info['filename']}

## Source Information

| Field | Value |
|-------|-------|
| Source | {task_info['source']} |
| Priority | {task_info['priority']} |
| Created | {task_info['created_at']} |
| Original File | `{task_info['filename']}` |

---

## Reasoning Analysis

### Task Category
{task_info['source']} → Requires {len(action_items)} action steps

### Human-in-the-Loop Checkpoints
Based on Company Handbook rules, the following actions require human approval:
- All external communications (email, WhatsApp, LinkedIn)
- Payments to new recipients
- Transactions over $100
- File deletions (we archive instead)

---

## Action Plan

{action_items_md}

---

## Execution Log

| Action ID | Started At | Completed At | Notes |
|-----------|------------|--------------|-------|
""" + '\n'.join([
    f"| {item['id']} | - | - | - |"
    for item in action_items
]) + f"""

---

## Notes & Observations

*Add any notes or observations during execution here*

---

## Completion Criteria

- [ ] All action items completed
- [ ] HITL approvals obtained where required
- [ ] Results logged
- [ ] Source file moved to Done/
- [ ] Dashboard updated

---

*Generated by Claude Reasoning Loop (Silver Tier)*
*Plan ID: {plan_id}*
"""


def create_plan(task_info: dict) -> Path:
    """Create a plan file for a task."""
    action_items = generate_action_items(task_info)
    plan_content = generate_plan_md(task_info, action_items)
    
    plan_filename = f"PLAN_{task_info['filename']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    plan_path = PLANS_PATH / plan_filename
    
    plan_path.write_text(plan_content, encoding='utf-8')
    
    log_message(f"Created plan: {plan_filename}")
    
    # Update state
    state = load_state()
    state['active_plans'].append({
        'plan_id': f"PLAN_{task_info['filename']}_{datetime.now().strftime('%Y%m%d')}",
        'file': str(plan_path),
        'status': 'draft',
        'created_at': datetime.now().isoformat()
    })
    state['processed_files'].append(task_info['filename'])
    save_state(state)
    
    return plan_path


def analyze_inbox() -> List[Path]:
    """Analyze inbox and needs_action folders, create plans for new items."""
    log_message("Analyzing inbox and needs_action folders...")
    
    state = load_state()
    processed = set(state.get('processed_files', []))
    created_plans = []
    
    # Process Inbox
    for file_path in INBOX_PATH.glob('*.md'):
        if file_path.name not in processed:
            log_message(f"Processing inbox item: {file_path.name}")
            task_info = extract_task_info(file_path)
            plan_path = create_plan(task_info)
            created_plans.append(plan_path)
    
    # Process Needs_Action
    for file_path in NEEDS_ACTION_PATH.glob('*.md'):
        if file_path.name not in processed:
            log_message(f"Processing needs_action item: {file_path.name}")
            task_info = extract_task_info(file_path)
            plan_path = create_plan(task_info)
            created_plans.append(plan_path)
    
    log_message(f"Created {len(created_plans)} new plans")
    return created_plans


def get_plan_status(plan_path: Path) -> dict:
    """Get the status of a plan file."""
    content = plan_path.read_text(encoding='utf-8')
    
    # Extract frontmatter
    status = 'unknown'
    total_actions = 0
    completed_actions = 0
    
    fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        fm_content = fm_match.group(1)
        for line in fm_content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key == 'status':
                    status = value
                elif key == 'total_actions':
                    total_actions = int(value)
                elif key == 'completed_actions':
                    completed_actions = int(value)
    
    # Count checkboxes
    checked = len(re.findall(r'^- \[x\]', content, re.MULTILINE))
    unchecked = len(re.findall(r'^- \[ \]', content, re.MULTILINE))
    
    return {
        'file': str(plan_path),
        'filename': plan_path.name,
        'status': status,
        'total_actions': total_actions or (checked + unchecked),
        'completed_actions': completed_actions or checked,
        'pending_actions': unchecked,
        'progress': f"{checked}/{checked + unchecked}" if (checked + unchecked) > 0 else "0/0"
    }


def show_status():
    """Show status of all plans."""
    log_message("Plan Status Report")
    print("\n" + "="*60)
    print("PLAN STATUS REPORT")
    print("="*60 + "\n")
    
    plans = list(PLANS_PATH.glob('PLAN_*.md'))
    
    if not plans:
        print("No plans found.")
        return
    
    statuses = [get_plan_status(p) for p in plans]
    
    # Summary
    total = len(statuses)
    completed = sum(1 for s in statuses if s['status'] == 'completed')
    in_progress = sum(1 for s in statuses if s['status'] == 'in_progress')
    draft = sum(1 for s in statuses if s['status'] == 'draft')
    pending_approval = sum(1 for s in statuses if s['status'] == 'pending_approval')
    
    print(f"Total Plans: {total}")
    print(f"  - Draft: {draft}")
    print(f"  - In Progress: {in_progress}")
    print(f"  - Pending Approval: {pending_approval}")
    print(f"  - Completed: {completed}")
    print("\n" + "-"*60)
    
    # Details
    for status in sorted(statuses, key=lambda x: x['filename']):
        progress_bar = "█" * int(50 * status['completed_actions'] / max(1, status['total_actions']))
        progress_bar = progress_bar.ljust(50, "░")
        
        print(f"\n{status['filename']}")
        print(f"  Status: {status['status']}")
        print(f"  Progress: [{progress_bar}] {status['progress']}")
    
    print("\n" + "="*60)


def process_plans():
    """Process pending plans - check for approvals and update status."""
    log_message("Processing plans...")
    
    state = load_state()
    
    for plan in list(PLANS_PATH.glob('PLAN_*.md')):
        status = get_plan_status(plan)
        
        # Check if all actions are complete
        if status['pending_actions'] == 0 and status['total_actions'] > 0:
            # Update plan status to completed
            content = plan.read_text(encoding='utf-8')
            content = re.sub(r'^status: .+$', 'status: completed', content, flags=re.MULTILINE)
            content = re.sub(r'^completed_actions: \d+$', f"completed_actions: {status['completed_actions']}", content, flags=re.MULTILINE)
            plan.write_text(content, encoding='utf-8')
            
            log_message(f"Plan completed: {plan.name}")
            
            # Move to Done
            done_path = DONE_PATH / plan.name
            plan.rename(done_path)
            
            # Update state
            state['active_plans'] = [p for p in state['active_plans'] if p['file'] != str(plan)]
            save_state(state)
    
    log_message("Plan processing complete")


def main():
    parser = argparse.ArgumentParser(description='Claude Reasoning Loop for AI Employee')
    parser.add_argument('--analyze', action='store_true', help='Analyze inbox and create plans')
    parser.add_argument('--process', action='store_true', help='Process pending plans')
    parser.add_argument('--status', action='store_true', help='Show status of all plans')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_inbox()
    elif args.process:
        process_plans()
    elif args.status:
        show_status()
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python claude_reasoning_loop.py --analyze")
        print("  python claude_reasoning_loop.py --status")
        print("  python claude_reasoning_loop.py --process")


if __name__ == '__main__':
    main()
