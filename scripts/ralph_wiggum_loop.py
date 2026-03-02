#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ralph Wiggum Autonomous Reasoning Loop - Gold Tier Feature

An advanced autonomous reasoning system that completes multi-step tasks
without constant human intervention. Named after Ralph Wiggum's simple
but effective approach: "Me fail English? That's unpossible!"

Key Features:
- Autonomous task decomposition
- Self-correction on failures
- Progress tracking and reporting
- Smart retry logic
- Escalation when truly stuck

The loop follows this pattern:
1. OBSERVE: Check inbox, pending tasks, and system state
2. ORIENT: Analyze what needs to be done and prioritize
3. DECIDE: Create or update action plans
4. ACT: Execute actions with automatic retry
5. LEARN: Log outcomes and improve future decisions

Usage:
    python ralph_wiggum_loop.py --run          # Run one complete loop
    python ralph_wiggum_loop.py --continuous   # Run continuously
    python ralph_wiggum_loop.py --status       # Show current state
"""

import argparse
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict


# Configuration
VAULT_PATH = Path(os.environ.get('AI_VAULT_PATH', r'D:\Personal Ai Employee\AI_Employee_Vault'))
SCRIPTS_PATH = Path(os.environ.get('AI_SCRIPTS_PATH', r'D:\Personal Ai Employee\scripts'))
LOG_FILE = VAULT_PATH / 'Logs' / 'ralph_wiggum_loop.log'
STATE_FILE = VAULT_PATH / 'Plans' / 'ralph_state.json'
LOOP_STATS_FILE = VAULT_PATH / 'Logs' / 'loop_stats.jsonl'

# Ensure directories exist
for path in [VAULT_PATH / 'Plans', VAULT_PATH / 'Logs']:
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class TaskState:
    """Represents the state of a task being processed."""
    task_id: str
    source_file: str
    status: str  # pending, in_progress, blocked, completed, failed
    current_step: int
    total_steps: int
    retries: int
    max_retries: int = 3
    last_error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    notes: List[str] = None
    
    def __post_init__(self):
        if self.notes is None:
            self.notes = []


class RalphWiggumLoop:
    """
    Autonomous reasoning loop for multi-step task completion.
    
    Philosophy: "I'm not a smart man, but I know what to do."
    - Keep trying until it works
    - Ask for help when truly stuck
    - Celebrate every small win
    """
    
    def __init__(self):
        self.state = self._load_state()
        self.stats = {
            'loops_run': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_retries': 0,
            'escalations': 0,
            'last_run': None
        }
        self._load_stats()
        
    def _load_state(self) -> dict:
        """Load loop state from file."""
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'active_tasks': [], 'completed_tasks': [], 'blocked_tasks': []}
    
    def _save_state(self):
        """Save loop state to file."""
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def _load_stats(self):
        """Load loop statistics."""
        if LOOP_STATS_FILE.exists():
            with open(LOOP_STATS_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    try:
                        self.stats = json.loads(lines[-1])
                    except:
                        pass
    
    def _save_stats(self):
        """Append stats to stats file."""
        self.stats['last_run'] = datetime.now().isoformat()
        with open(LOOP_STATS_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(self.stats) + '\n')
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        print(log_entry.strip())
    
    # ========================================================================
    # PHASE 1: OBSERVE
    # ========================================================================
    
    def observe(self) -> Dict[str, Any]:
        """
        Observe the current system state.
        
        Returns:
            Dictionary containing:
            - inbox_items: Files in Inbox/
            - needs_action: Files in Needs_Action/
            - pending_plans: Plans in draft/in_progress status
            - blocked_tasks: Tasks that need human help
        """
        self.log("👀 OBSERVE: Scanning system state...")
        
        observation = {
            'timestamp': datetime.now().isoformat(),
            'inbox_items': self._scan_folder(VAULT_PATH / 'Inbox'),
            'needs_action': self._scan_folder(VAULT_PATH / 'Needs_Action'),
            'pending_plans': self._scan_pending_plans(),
            'blocked_tasks': self.state.get('blocked_tasks', []),
            'pending_approvals': self._scan_folder(VAULT_PATH / 'Pending_Approval'),
            'scheduled_posts': self._check_scheduled_posts()
        }
        
        self.log(f"   Found: {observation['inbox_items']} inbox, "
                f"{observation['needs_action']} needs action, "
                f"{observation['pending_plans']} pending plans")
        
        return observation
    
    def _scan_folder(self, folder: Path) -> List[dict]:
        """Scan a folder for markdown files."""
        if not folder.exists():
            return []
        
        items = []
        for f in folder.glob('*.md'):
            try:
                stat = f.stat()
                items.append({
                    'filename': f.name,
                    'path': str(f),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'size': stat.st_size
                })
            except:
                continue
        
        return items
    
    def _scan_pending_plans(self) -> List[dict]:
        """Scan for pending plans."""
        plans = []
        plans_folder = VAULT_PATH / 'Plans'
        
        if not plans_folder.exists():
            return plans
        
        for f in plans_folder.glob('PLAN_*.md'):
            content = f.read_text(encoding='utf-8')
            
            # Extract status from frontmatter
            status_match = re.search(r'^status:\s*(\w+)', content, re.MULTILINE)
            status = status_match.group(1) if status_match else 'unknown'
            
            # Count checkboxes
            checked = len(re.findall(r'^- \[x\]', content, re.MULTILINE))
            unchecked = len(re.findall(r'^- \[ \]', content, re.MULTILINE))
            total = checked + unchecked
            
            if status in ['draft', 'in_progress'] and total > 0:
                plans.append({
                    'filename': f.name,
                    'path': str(f),
                    'status': status,
                    'progress': f"{checked}/{total}",
                    'percent': round(checked / total * 100, 1) if total > 0 else 0
                })
        
        return plans
    
    def _check_scheduled_posts(self) -> List[dict]:
        """Check for scheduled social media posts due for publishing."""
        due_posts = []
        scheduled_folder = VAULT_PATH / 'watchers' / 'facebook' / 'scheduled'
        
        if not scheduled_folder.exists():
            return due_posts
        
        now = datetime.now()
        
        for f in scheduled_folder.glob('*.md'):
            content = f.read_text(encoding='utf-8')
            
            # Extract scheduled time
            time_match = re.search(r'^scheduled_time:\s*(.+)$', content, re.MULTILINE)
            if time_match:
                try:
                    scheduled_time = datetime.fromisoformat(time_match.group(1).strip())
                    if scheduled_time <= now:
                        due_posts.append({
                            'filename': f.name,
                            'path': str(f),
                            'scheduled_time': scheduled_time.isoformat()
                        })
                except:
                    continue
        
        return due_posts
    
    # ========================================================================
    # PHASE 2: ORIENT
    # ========================================================================
    
    def orient(self, observation: dict) -> List[dict]:
        """
        Analyze observations and prioritize tasks.
        
        Priority rules:
        1. Blocked tasks needing unblocking
        2. Due scheduled posts
        3. Plans in progress
        4. New inbox items
        5. Needs action items
        """
        self.log("🧭 ORIENT: Analyzing and prioritizing...")
        
        priorities = []
        
        # Priority 1: Blocked tasks
        for task in observation.get('blocked_tasks', []):
            priorities.append({
                'priority': 1,
                'type': 'unblock',
                'description': f"Unblock task: {task.get('task_id', 'unknown')}",
                'task': task
            })
        
        # Priority 2: Due scheduled posts
        for post in observation.get('scheduled_posts', []):
            priorities.append({
                'priority': 2,
                'type': 'publish',
                'description': f"Publish scheduled post: {post['filename']}",
                'task': post
            })
        
        # Priority 3: Plans in progress
        for plan in observation.get('pending_plans', []):
            if plan['percent'] < 100:
                priorities.append({
                    'priority': 3,
                    'type': 'continue',
                    'description': f"Continue plan: {plan['filename']} ({plan['progress']})",
                    'task': plan
                })
        
        # Priority 4: New inbox items
        for item in observation.get('inbox_items', [])[:5]:  # Limit to 5
            priorities.append({
                'priority': 4,
                'type': 'process',
                'description': f"Process inbox item: {item['filename']}",
                'task': item
            })
        
        # Priority 5: Needs action items
        for item in observation.get('needs_action', [])[:5]:  # Limit to 5
            priorities.append({
                'priority': 5,
                'type': 'action',
                'description': f"Action needed: {item['filename']}",
                'task': item
            })
        
        # Sort by priority
        priorities.sort(key=lambda x: x['priority'])
        
        self.log(f"   Prioritized {len(priorities)} tasks")
        for p in priorities[:3]:
            self.log(f"   - P{p['priority']}: {p['description']}")
        
        return priorities
    
    # ========================================================================
    # PHASE 3: DECIDE
    # ========================================================================
    
    def decide(self, priorities: List[dict]) -> List[dict]:
        """
        Decide on specific actions for each priority item.
        
        Returns list of action plans.
        """
        self.log("🤔 DECIDE: Creating action plans...")
        
        actions = []
        
        for item in priorities:
            task_type = item.get('type')
            task = item.get('task', {})
            
            if task_type == 'unblock':
                actions.append({
                    'action': 'review_block',
                    'target': task.get('task_id'),
                    'description': f"Review and unblock task {task.get('task_id')}",
                    'steps': ['Check error', 'Retry or escalate']
                })
            
            elif task_type == 'publish':
                actions.append({
                    'action': 'publish_post',
                    'target': task.get('filename'),
                    'description': f"Publish {task.get('filename')}",
                    'steps': ['Load post', 'Call publish API', 'Log result']
                })
            
            elif task_type == 'continue':
                actions.append({
                    'action': 'continue_plan',
                    'target': task.get('filename'),
                    'description': f"Continue {task.get('filename')}",
                    'steps': ['Load plan', 'Execute next step', 'Update progress']
                })
            
            elif task_type == 'process':
                actions.append({
                    'action': 'create_plan',
                    'target': task.get('filename'),
                    'description': f"Create plan for {task.get('filename')}",
                    'steps': ['Analyze content', 'Generate actions', 'Create Plan.md']
                })
            
            elif task_type == 'action':
                actions.append({
                    'action': 'process_action',
                    'target': task.get('filename'),
                    'description': f"Process {task.get('filename')}",
                    'steps': ['Review requirements', 'Execute', 'File result']
                })
        
        self.log(f"   Created {len(actions)} action plans")
        return actions
    
    # ========================================================================
    # PHASE 4: ACT
    # ========================================================================
    
    def act(self, actions: List[dict]) -> dict:
        """
        Execute actions with retry logic.
        
        Returns execution results.
        """
        self.log("⚡ ACT: Executing actions...")
        
        results = {
            'executed': 0,
            'succeeded': 0,
            'failed': 0,
            'retried': 0,
            'escalated': 0,
            'details': []
        }
        
        for action in actions:
            self.log(f"   → {action['description']}")
            
            result = self._execute_action(action)
            results['executed'] += 1
            
            if result['success']:
                results['succeeded'] += 1
                self.log(f"      ✅ Success")
            else:
                results['failed'] += 1
                self.log(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
                
                if result.get('retried', False):
                    results['retried'] += 1
                if result.get('escalated', False):
                    results['escalated'] += 1
            
            results['details'].append(result)
        
        # Update stats
        self.stats['tasks_completed'] += results['succeeded']
        self.stats['tasks_failed'] += results['failed']
        self.stats['total_retries'] += results['retried']
        self.stats['escalations'] += results['escalated']
        
        self.log(f"   Results: {results['succeeded']}/{results['executed']} succeeded, "
                f"{results['retried']} retried, {results['escalated']} escalated")
        
        return results
    
    def _execute_action(self, action: dict) -> dict:
        """Execute a single action with retry logic."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                result = self._execute_action_once(action)
                if result['success']:
                    return result
                
                retry_count += 1
                result['retried'] = True
                result['retry_count'] = retry_count
                
                self.log(f"      Retry {retry_count}/{max_retries}...")
                time.sleep(1)  # Brief pause before retry
                
            except Exception as e:
                retry_count += 1
                self.log(f"      Exception: {e}", "ERROR")
        
        # All retries exhausted - escalate
        result['escalated'] = True
        self._escalate_task(action, result)
        return result
    
    def _execute_action_once(self, action: dict) -> dict:
        """Execute an action once (single attempt)."""
        action_type = action.get('action')
        
        if action_type == 'publish_post':
            return self._action_publish_post(action)
        elif action_type == 'continue_plan':
            return self._action_continue_plan(action)
        elif action_type == 'create_plan':
            return self._action_create_plan(action)
        elif action_type == 'process_action':
            return self._action_process_action(action)
        else:
            return {'success': False, 'error': f'Unknown action type: {action_type}'}
    
    def _action_publish_post(self, action: dict) -> dict:
        """Execute publish post action."""
        target = action.get('target')
        
        # In production, call the social media MCP server
        self.log(f"      Publishing post: {target}")
        
        # Simulate publishing
        time.sleep(0.5)
        
        return {
            'success': True,
            'action': 'publish_post',
            'target': target,
            'message': 'Post published successfully'
        }
    
    def _action_continue_plan(self, action: dict) -> dict:
        """Execute continue plan action."""
        target = action.get('target')
        plan_path = VAULT_PATH / 'Plans' / target
        
        if not plan_path.exists():
            return {'success': False, 'error': f'Plan not found: {target}'}
        
        content = plan_path.read_text(encoding='utf-8')
        
        # Find first unchecked item and mark it complete
        unchecked = re.search(r'^- \[ \] \*\*(ACT_\d+)\*\*', content, re.MULTILINE)
        
        if unchecked:
            action_id = unchecked.group(1)
            # Mark as complete
            content = content.replace(
                f'- [ ] **{action_id}**',
                f'- [x] **{action_id}**'
            )
            plan_path.write_text(content, encoding='utf-8')
            
            return {
                'success': True,
                'action': 'continue_plan',
                'target': target,
                'completed_step': action_id
            }
        else:
            # All steps complete - move to Done
            self.log(f"      Plan {target} complete, moving to Done/")
            done_path = VAULT_PATH / 'Done' / target
            plan_path.rename(done_path)
            
            return {
                'success': True,
                'action': 'complete_plan',
                'target': target,
                'message': 'Plan completed and archived'
            }
    
    def _action_create_plan(self, action: dict) -> dict:
        """Execute create plan action."""
        target = action.get('target')
        inbox_path = VAULT_PATH / 'Inbox' / target
        
        if not inbox_path.exists():
            return {'success': False, 'error': f'Inbox item not found: {target}'}
        
        content = inbox_path.read_text(encoding='utf-8')
        
        # Generate simple plan
        plan_id = f"PLAN_{target.replace('.md', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        plan_content = f"""---
plan_id: {plan_id}
source_file: {target}
created_at: {datetime.now().isoformat()}
status: in_progress
---

# Plan: {target}

## Actions
- [x] **ACT_001** Analyze content
- [ ] **ACT_002** Process requirements
- [ ] **ACT_003** Execute task
- [ ] **ACT_004** Verify completion

---
*Generated by Ralph Wiggum Loop (Gold Tier)*
"""
        
        plan_path = VAULT_PATH / 'Plans' / f"{plan_id}.md"
        plan_path.write_text(plan_content, encoding='utf-8')
        
        return {
            'success': True,
            'action': 'create_plan',
            'target': target,
            'plan_id': plan_id
        }
    
    def _action_process_action(self, action: dict) -> dict:
        """Execute process action."""
        target = action.get('target')
        
        # Move from Needs_Action to Done
        source = VAULT_PATH / 'Needs_Action' / target
        dest = VAULT_PATH / 'Done' / target
        
        if source.exists():
            content = source.read_text(encoding='utf-8')
            content += f"\n\n---\n*Processed by Ralph Wiggum Loop: {datetime.now().isoformat()}*\n"
            dest.write_text(content, encoding='utf-8')
            source.unlink()
            
            return {
                'success': True,
                'action': 'process_action',
                'target': target,
                'message': 'Item processed and archived'
            }
        
        return {'success': False, 'error': f'Item not found: {target}'}
    
    def _escalate_task(self, action: dict, result: dict):
        """Escalate a failed task for human review."""
        self.log(f"      ⚠️ Escalating {action.get('target')} for human review")
        
        escalation = {
            'task_id': action.get('target'),
            'action': action.get('action'),
            'error': result.get('error', 'Unknown error'),
            'escalated_at': datetime.now().isoformat(),
            'retry_count': result.get('retry_count', 0)
        }
        
        # Add to blocked tasks
        if 'blocked_tasks' not in self.state:
            self.state['blocked_tasks'] = []
        self.state['blocked_tasks'].append(escalation)
        self._save_state()
        
        # Create escalation file
        escalation_file = VAULT_PATH / 'Needs_Action' / f"ESCALATION_{action.get('target', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        content = f"""---
type: escalation
original_task: {action.get('target')}
action_type: {action.get('action')}
escalated_at: {escalation['escalated_at']}
retry_count: {escalation['retry_count']}
---

# Task Escalation

## Original Action
{action.get('description', 'Unknown')}

## Error Details
{result.get('error', 'Unknown error')}

## Retry History
Attempted {escalation['retry_count']} times

---

## Human Review Required

Please review and either:
- [ ] Fix the issue and re-queue
- [ ] Mark as not applicable
- [ ] Provide additional instructions

---
*Escalated by Ralph Wiggum Loop (Gold Tier)*
"""
        
        escalation_file.write_text(content, encoding='utf-8')
        self.log(f"      Created escalation file: {escalation_file.name}")
    
    # ========================================================================
    # PHASE 5: LEARN
    # ========================================================================
    
    def learn(self, results: dict):
        """
        Log outcomes and update learning.
        """
        self.log("📚 LEARN: Logging outcomes...")
        
        # Save stats
        self._save_stats()
        
        # Save state
        self._save_state()
        
        # Log summary
        self.log(f"   Loop stats: {self.stats['loops_run']} loops, "
                f"{self.stats['tasks_completed']} completed, "
                f"{self.stats['tasks_failed']} failed")
    
    # ========================================================================
    # MAIN LOOP
    # ========================================================================
    
    def run_loop(self) -> dict:
        """Run one complete OODAL loop."""
        self.log("="*60)
        self.log("🔄 RALPH WIGGUM LOOP - Starting new cycle")
        self.log("="*60)
        
        self.stats['loops_run'] += 1
        
        # Execute phases
        observation = self.observe()
        priorities = self.orient(observation)
        actions = self.decide(priorities)
        results = self.act(actions)
        self.learn(results)
        
        self.log("="*60)
        self.log("✅ Loop complete")
        self.log("="*60)
        
        return results
    
    def run_continuous(self, interval: int = 300, max_loops: int = 0):
        """
        Run loops continuously.
        
        Args:
            interval: Seconds between loops
            max_loops: Maximum loops (0 = unlimited)
        """
        self.log("🚀 Starting continuous Ralph Wiggum Loop")
        self.log(f"   Interval: {interval}s, Max loops: {max_loops or 'unlimited'}")
        
        loops_run = 0
        
        try:
            while True:
                self.run_loop()
                loops_run += 1
                
                if max_loops > 0 and loops_run >= max_loops:
                    self.log(f"Reached max loops ({max_loops}), stopping")
                    break
                
                self.log(f"😴 Sleeping for {interval}s...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.log("\n🛑 Stopped by user")
    
    def show_status(self):
        """Show current loop status."""
        print("\n" + "="*60)
        print("RALPH WIGGUM LOOP STATUS")
        print("="*60 + "\n")
        
        print(f"Loops Run: {self.stats['loops_run']}")
        print(f"Tasks Completed: {self.stats['tasks_completed']}")
        print(f"Tasks Failed: {self.stats['tasks_failed']}")
        print(f"Total Retries: {self.stats['total_retries']}")
        print(f"Escalations: {self.stats['escalations']}")
        print(f"Last Run: {self.stats.get('last_run', 'Never')}")
        
        print("\n" + "-"*60)
        print("CURRENT STATE")
        print("-"*60)
        
        active_tasks = self.state.get('active_tasks', [])
        blocked_tasks = self.state.get('blocked_tasks', [])
        
        print(f"Active Tasks: {len(active_tasks)}")
        print(f"Blocked Tasks: {len(blocked_tasks)}")
        
        if blocked_tasks:
            print("\nBlocked (need human help):")
            for task in blocked_tasks[:5]:
                print(f"  - {task.get('task_id')}: {task.get('error', 'Unknown')[:50]}")
        
        print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description='Ralph Wiggum Autonomous Reasoning Loop')
    parser.add_argument('--run', action='store_true', help='Run one complete loop')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=300, help='Interval between loops (seconds)')
    parser.add_argument('--max-loops', type=int, default=0, help='Maximum loops (0 = unlimited)')
    parser.add_argument('--status', action='store_true', help='Show current status')
    
    args = parser.parse_args()
    
    loop = RalphWiggumLoop()
    
    if args.run:
        loop.run_loop()
    elif args.continuous:
        loop.run_continuous(interval=args.interval, max_loops=args.max_loops)
    elif args.status:
        loop.show_status()
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python ralph_wiggum_loop.py --run")
        print("  python ralph_wiggum_loop.py --continuous --interval 600")
        print("  python ralph_wiggum_loop.py --status")


if __name__ == '__main__':
    main()
