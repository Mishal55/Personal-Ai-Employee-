#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced CEO Briefing Generator - Gold Tier Feature

Generates comprehensive weekly/monthly CEO briefings with:
- Revenue and financial metrics (from Odoo)
- Bottleneck analysis
- Proactive suggestions
- Task completion statistics
- Social media performance

Usage:
    python ceo_briefing_generator.py --weekly    # Generate weekly briefing
    python ceo_briefing_generator.py --monthly   # Generate monthly briefing
    python ceo_briefing_generator.py --preview   # Preview without saving
"""

import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List


# Configuration
VAULT_PATH = Path(os.environ.get('AI_VAULT_PATH', r'D:\Personal Ai Employee\AI_Employee_Vault'))
BRIEFINGS_PATH = VAULT_PATH / 'Briefings' / 'CEO'
LOGS_PATH = VAULT_PATH / 'Logs'
ACCOUNTING_LOG = VAULT_PATH / 'Accounting' / 'Odoo' / 'transactions.jsonl'
APPROVAL_LOG = LOGS_PATH / 'approvals.jsonl'
LOOP_STATS_LOG = LOGS_PATH / 'loop_stats.jsonl'

BRIEFINGS_PATH.mkdir(parents=True, exist_ok=True)


def load_jsonl_file(filepath: Path) -> List[dict]:
    """Load a JSONL file and return list of entries."""
    entries = []
    if not filepath.exists():
        return entries
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except:
                continue
    return entries


def count_files_in_folder(folder: Path) -> int:
    """Count markdown files in a folder."""
    if not folder.exists():
        return 0
    return len(list(folder.glob('*.md')))


def get_files_by_date_range(folder: Path, days: int) -> List[Path]:
    """Get files modified in the last N days."""
    if not folder.exists():
        return []
    
    cutoff = datetime.now() - timedelta(days=days)
    files = []
    
    for f in folder.glob('*.md'):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime >= cutoff:
                files.append(f)
        except:
            continue
    
    return files


def analyze_bottlenecks() -> List[dict]:
    """Analyze system for bottlenecks and issues."""
    bottlenecks = []
    
    # Check Pending_Approval count
    pending_count = count_files_in_folder(VAULT_PATH / 'Pending_Approval')
    if pending_count > 10:
        bottlenecks.append({
            'type': 'approval_backlog',
            'severity': 'high',
            'description': f'{pending_count} items awaiting approval',
            'suggestion': 'Schedule dedicated approval time or delegate authority'
        })
    elif pending_count > 5:
        bottlenecks.append({
            'type': 'approval_backlog',
            'severity': 'medium',
            'description': f'{pending_count} items awaiting approval',
            'suggestion': 'Consider batch approval process'
        })
    
    # Check Inbox count
    inbox_count = count_files_in_folder(VAULT_PATH / 'Inbox')
    if inbox_count > 20:
        bottlenecks.append({
            'type': 'inbox_backlog',
            'severity': 'high',
            'description': f'{inbox_count} items in inbox',
            'suggestion': 'Run Ralph Wiggum loop to process inbox automatically'
        })
    
    # Check Needs_Action count
    needs_action_count = count_files_in_folder(VAULT_PATH / 'Needs_Action')
    if needs_action_count > 10:
        bottlenecks.append({
            'type': 'action_backlog',
            'severity': 'medium',
            'description': f'{needs_action_count} items need action',
            'suggestion': 'Review and prioritize or escalate'
        })
    
    # Check for escalations
    escalations = get_files_by_date_range(VAULT_PATH / 'Needs_Action', 7)
    escalation_count = sum(1 for f in escalations if 'ESCALATION' in f.name)
    if escalation_count > 3:
        bottlenecks.append({
            'type': 'frequent_escalations',
            'severity': 'high',
            'description': f'{escalation_count} escalations this week',
            'suggestion': 'Review escalation patterns and update automation rules'
        })
    
    # Check for old pending plans
    plans_folder = VAULT_PATH / 'Plans'
    old_plans = []
    if plans_folder.exists():
        for f in plans_folder.glob('PLAN_*.md'):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                age = (datetime.now() - mtime).days
                if age > 7:
                    content = f.read_text(encoding='utf-8')
                    if 'status: in_progress' in content:
                        old_plans.append(f.name)
            except:
                continue
    
    if old_plans:
        bottlenecks.append({
            'type': 'stale_plans',
            'severity': 'medium',
            'description': f'{len(old_plans)} plans inactive for 7+ days',
            'suggestion': 'Review and complete or close stale plans'
        })
    
    return bottlenecks


def generate_proactive_suggestions(bottlenecks: List[dict], stats: dict) -> List[dict]:
    """Generate proactive suggestions based on analysis."""
    suggestions = []
    
    # Based on bottlenecks
    for bottleneck in bottlenecks:
        suggestions.append({
            'category': 'bottleneck_resolution',
            'priority': 'high' if bottleneck['severity'] == 'high' else 'medium',
            'suggestion': bottleneck['suggestion'],
            'reason': bottleneck['description']
        })
    
    # Based on completion rate
    if stats.get('completion_rate', 100) < 80:
        suggestions.append({
            'category': 'productivity',
            'priority': 'high',
            'suggestion': 'Review task complexity and break down large tasks',
            'reason': f"Task completion rate is {stats.get('completion_rate', 0)}%"
        })
    
    # Based on approval patterns
    if stats.get('approval_rate', 100) < 90:
        suggestions.append({
            'category': 'approval_process',
            'priority': 'medium',
            'suggestion': 'Review approval criteria - high rejection rate detected',
            'reason': f"Approval rate is {stats.get('approval_rate', 0)}%"
        })
    
    # Default suggestions if none generated
    if not suggestions:
        suggestions = [
            {
                'category': 'optimization',
                'priority': 'low',
                'suggestion': 'Consider automating more routine tasks',
                'reason': 'System running smoothly - opportunity for expansion'
            },
            {
                'category': 'review',
                'priority': 'low',
                'suggestion': 'Update Company Handbook with recent learnings',
                'reason': 'Continuous improvement opportunity'
            }
        ]
    
    return suggestions


def calculate_financial_stats(days: int) -> dict:
    """Calculate financial statistics from accounting logs."""
    transactions = load_jsonl_file(ACCOUNTING_LOG)
    
    # Filter by date
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    recent = [t for t in transactions if t.get('date', '') >= cutoff]
    
    revenue = sum(t.get('amount', 0) for t in recent if t.get('type') == 'revenue')
    expenses = sum(t.get('amount', 0) for t in recent if t.get('type') == 'expense')
    
    # Get invoice stats
    invoices_created = sum(1 for t in recent if t.get('type') == 'invoice_created')
    invoices_paid = sum(1 for t in recent if t.get('type') == 'payment_received')
    
    return {
        'revenue': revenue,
        'expenses': expenses,
        'net': revenue - expenses,
        'invoices_created': invoices_created,
        'invoices_paid': invoices_paid,
        'transaction_count': len(recent)
    }


def calculate_activity_stats(days: int) -> dict:
    """Calculate activity statistics."""
    approvals = load_jsonl_file(APPROVAL_LOG)
    loop_stats = load_jsonl_file(LOOP_STATS_LOG)
    
    # Filter by date
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    recent_approvals = [a for a in approvals if a.get('timestamp', '')[:10] >= cutoff]
    
    approved = sum(1 for a in recent_approvals if a.get('action') == 'approve')
    rejected = sum(1 for a in recent_approvals if a.get('action') == 'reject')
    
    # Loop stats
    total_loops = len(loop_stats)
    total_completed = sum(s.get('tasks_completed', 0) for s in loop_stats[-30:])  # Last 30 loops
    total_failed = sum(s.get('tasks_failed', 0) for s in loop_stats[-30:])
    
    # Folder counts
    inbox_count = count_files_in_folder(VAULT_PATH / 'Inbox')
    pending_count = count_files_in_folder(VAULT_PATH / 'Pending_Approval')
    done_count = len(get_files_by_date_range(VAULT_PATH / 'Done', days))
    
    return {
        'approvals_processed': len(recent_approvals),
        'approved': approved,
        'rejected': rejected,
        'approval_rate': round(approved / max(1, len(recent_approvals)) * 100, 1),
        'loops_run': total_loops,
        'tasks_completed': total_completed,
        'tasks_failed': total_failed,
        'completion_rate': round(total_completed / max(1, total_completed + total_failed) * 100, 1),
        'inbox_count': inbox_count,
        'pending_count': pending_count,
        'done_count': done_count
    }


def generate_weekly_briefing() -> str:
    """Generate a comprehensive weekly CEO briefing."""
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    
    # Gather statistics
    financial_stats = calculate_financial_stats(7)
    activity_stats = calculate_activity_stats(7)
    bottlenecks = analyze_bottlenecks()
    suggestions = generate_proactive_suggestions(bottlenecks, activity_stats)
    
    # Determine overall status
    if len(bottlenecks) == 0:
        overall_status = "🟢 Excellent"
    elif len([b for b in bottlenecks if b['severity'] == 'high']) == 0:
        overall_status = "🟡 Good"
    else:
        overall_status = "🔴 Needs Attention"
    
    content = f"""---
type: weekly_ceo_briefing
period_start: {week_ago.strftime('%Y-%m-%d')}
period_end: {now.strftime('%Y-%m-%d')}
generated_at: {now.isoformat()}
status: {overall_status}
---

# 📈 Weekly CEO Briefing

## Executive Summary

**Week of {week_ago.strftime('%B %d')} to {now.strftime('%B %d, %Y')}**

| Overall Status | Tasks Completed | Approvals Processed | Net Revenue |
|----------------|-----------------|---------------------|-------------|
| {overall_status} | {activity_stats['done_count']} | {activity_stats['approvals_processed']} | ${financial_stats['net']:,.2f} |

---

## 💰 Financial Performance

### Revenue & Expenses

| Metric | This Week | Status |
|--------|-----------|--------|
| Revenue | ${financial_stats['revenue']:,.2f} | {"🟢" if financial_stats['revenue'] > 0 else "⚪"} |
| Expenses | ${financial_stats['expenses']:,.2f} | - |
| **Net Income** | **${financial_stats['net']:,.2f}** | {"🟢" if financial_stats['net'] > 0 else "🔴"} |

### Invoicing

| Metric | Count |
|--------|-------|
| Invoices Created | {financial_stats['invoices_created']} |
| Invoices Paid | {financial_stats['invoices_paid']} |
| Payment Rate | {round(financial_stats['invoices_paid'] / max(1, financial_stats['invoices_created']) * 100, 1)}% |

---

## 📊 Activity Metrics

### Task Processing

| Metric | Value | Trend |
|--------|-------|-------|
| Tasks Completed | {activity_stats['done_count']} | {"📈" if activity_stats['done_count'] > 5 else "📊"} |
| Loops Run | {activity_stats['loops_run']} | - |
| Completion Rate | {activity_stats['completion_rate']}% | {"✅" if activity_stats['completion_rate'] > 80 else "⚠️"} |

### Approval Workflow

| Metric | Value |
|--------|-------|
| Total Approvals | {activity_stats['approvals_processed']} |
| Approved | {activity_stats['approved']} |
| Rejected | {activity_stats['rejected']} |
| Approval Rate | {activity_stats['approval_rate']}% |

### Current Backlog

| Queue | Count |
|-------|-------|
| Inbox | {activity_stats['inbox_count']} |
| Pending Approval | {activity_stats['pending_count']} |

---

## 🚨 Bottleneck Analysis

"""
    
    if bottlenecks:
        content += "| Severity | Issue | Suggestion |\n"
        content += "|----------|-------|------------|\n"
        for b in bottlenecks:
            icon = "🔴" if b['severity'] == 'high' else "🟡"
            content += f"| {icon} | {b['description']} | {b['suggestion']} |\n"
    else:
        content += "✅ **No significant bottlenecks detected**\n"
    
    content += f"""
---

## 💡 Proactive Suggestions

"""
    
    for i, s in enumerate(suggestions, 1):
        priority_icon = "🔴" if s['priority'] == 'high' else "🟡" if s['priority'] == 'medium' else "🟢"
        content += f"""### {i}. {s['category'].replace('_', ' ').title()}
- **Priority:** {priority_icon} {s['priority'].title()}
- **Suggestion:** {s['suggestion']}
- **Reason:** {s['reason']}

"""
    
    content += f"""---

## 📅 Next Week Priorities

1. {"Address high-priority bottlenecks" if any(b['severity'] == 'high' for b in bottlenecks) else "Maintain current momentum"}
2. Review and process remaining inbox items
3. Update automation rules based on escalation patterns

---

## 📝 Notes & Commentary

*This briefing was generated automatically by the AI Employee Gold Tier system.*

*For questions or to adjust briefing parameters, see the configuration in `scripts/ceo_briefing_generator.py`.*

---

**Generated:** {now.strftime('%Y-%m-%d %H:%M')}  
**AI Employee Version:** Gold Tier v0.3  
**Next Briefing:** {(now + timedelta(days=7)).strftime('%Y-%m-%d')}
"""
    
    return content


def generate_monthly_briefing() -> str:
    """Generate a comprehensive monthly CEO briefing."""
    now = datetime.now()
    month_ago = now - timedelta(days=30)
    
    # Gather statistics
    financial_stats = calculate_financial_stats(30)
    activity_stats = calculate_activity_stats(30)
    bottlenecks = analyze_bottlenecks()
    suggestions = generate_proactive_suggestions(bottlenecks, activity_stats)
    
    content = f"""---
type: monthly_ceo_briefing
period_start: {month_ago.strftime('%Y-%m-%d')}
period_end: {now.strftime('%Y-%m-%d')}
generated_at: {now.isoformat()}
---

# 📊 Monthly CEO Briefing

## {now.strftime('%B %Y')}

---

## Executive Summary

| Metric | This Month | Target | Status |
|--------|------------|--------|--------|
| Net Revenue | ${financial_stats['net']:,.2f} | $10,000 | {"✅" if financial_stats['net'] >= 10000 else "⏳"} |
| Tasks Completed | {activity_stats['done_count']} | 80 | {"✅" if activity_stats['done_count'] >= 80 else "⏳"} |
| Approval Rate | {activity_stats['approval_rate']}% | 95% | {"✅" if activity_stats['approval_rate'] >= 95 else "⏳"} |

---

## 💰 Financial Summary

### Income Statement

| Category | Amount |
|----------|--------|
| **Revenue** | ${financial_stats['revenue']:,.2f} |
| Expenses | ${financial_stats['expenses']:,.2f} |
| **Net Income** | **${financial_stats['net']:,.2f}** |

### Key Metrics

- Invoices Created: {financial_stats['invoices_created']}
- Invoices Paid: {financial_stats['invoices_paid']}
- Transactions: {financial_stats['transaction_count']}

---

## 📈 Activity Summary

| Metric | Value |
|--------|-------|
| Tasks Completed | {activity_stats['done_count']} |
| Loops Run | {activity_stats['loops_run']} |
| Approvals Processed | {activity_stats['approvals_processed']} |
| Completion Rate | {activity_stats['completion_rate']}% |

---

## 🚨 Key Issues

"""
    
    if bottlenecks:
        for b in bottlenecks:
            icon = "🔴" if b['severity'] == 'high' else "🟡"
            content += f"- {icon} **{b['type'].replace('_', ' ').title()}:** {b['description']}\n"
    else:
        content += "✅ No major issues this month\n"
    
    content += f"""
---

## 💡 Strategic Recommendations

"""
    
    for s in suggestions[:3]:
        content += f"- **{s['category'].replace('_', ' ').title()}:** {s['suggestion']}\n"
    
    content += f"""
---

## 🎯 Next Month Goals

1. Increase revenue by 10%
2. Maintain approval rate above 95%
3. Reduce average task completion time

---

**Generated:** {now.strftime('%Y-%m-%d %H:%M')}  
**AI Employee Gold Tier v0.3**
"""
    
    return content


def save_briefing(content: str, briefing_type: str) -> Path:
    """Save the briefing to the CEO briefings folder."""
    now = datetime.now()
    
    if briefing_type == 'weekly':
        filename = f"WEEKLY_CEO_BRIEFING_{now.strftime('%Y-W%W')}.md"
    else:
        filename = f"MONTHLY_CEO_BRIEFING_{now.strftime('%Y-%m')}.md"
    
    filepath = BRIEFINGS_PATH / filename
    filepath.write_text(content, encoding='utf-8')
    
    return filepath


def main():
    parser = argparse.ArgumentParser(description='CEO Briefing Generator (Gold Tier)')
    parser.add_argument('--weekly', action='store_true', help='Generate weekly briefing')
    parser.add_argument('--monthly', action='store_true', help='Generate monthly briefing')
    parser.add_argument('--preview', action='store_true', help='Preview without saving')
    
    args = parser.parse_args()
    
    if args.weekly:
        print("\n📝 Generating weekly CEO briefing...")
        content = generate_weekly_briefing()
    elif args.monthly:
        print("\n📝 Generating monthly CEO briefing...")
        content = generate_monthly_briefing()
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python ceo_briefing_generator.py --weekly")
        print("  python ceo_briefing_generator.py --monthly")
        print("  python ceo_briefing_generator.py --weekly --preview")
        return
    
    if args.preview:
        print("\n--- PREVIEW ---\n")
        print(content)
    else:
        filepath = save_briefing(content, 'weekly' if args.weekly else 'monthly')
        print(f"✅ Briefing saved to: {filepath}")
        print(f"\n--- Preview (first 500 chars) ---\n")
        print(content[:500] + "...")


if __name__ == '__main__':
    main()
