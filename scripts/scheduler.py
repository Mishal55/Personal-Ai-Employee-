#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Employee Scheduler - Silver Tier Feature

Manages scheduled tasks using Windows Task Scheduler or cron.
Provides configuration and execution of recurring AI Employee tasks.

Supported Schedules:
- WhatsApp watcher (continuous or periodic)
- LinkedIn post publisher (at scheduled times)
- Reasoning loop processor (periodic)
- Dashboard updater (daily)
- Weekly briefing generator (weekly)

Usage:
    python scheduler.py --install         # Install scheduled tasks
    python scheduler.py --uninstall       # Remove scheduled tasks
    python scheduler.py --status          # Show task status
    python scheduler.py --run <task>      # Run a specific task manually
    python scheduler.py --list            # List all configured tasks
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict


# Configuration
VAULT_PATH = Path(os.environ.get('AI_VAULT_PATH', r'D:\Personal Ai Employee\AI_Employee_Vault'))
SCRIPTS_PATH = Path(os.environ.get('AI_SCRIPTS_PATH', r'D:\Personal Ai Employee\scripts'))
CONFIG_PATH = Path(os.environ.get('AI_CONFIG_PATH', r'D:\Personal Ai Employee\config'))
LOG_FILE = VAULT_PATH / 'Logs' / 'scheduler.log'
SCHEDULE_STATE = CONFIG_PATH / 'scheduler_state.json'

# Ensure directories exist
CONFIG_PATH.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Task definitions
TASKS = {
    'whatsapp_watcher': {
        'name': 'AI_Employee_WhatsApp_Watcher',
        'description': 'Monitor WhatsApp Web for new messages',
        'script': 'whatsapp_watcher.py',
        'args': '--watch --interval 120',
        'schedule': 'continuous',  # Runs continuously
        'enabled': True
    },
    'linkedin_publisher': {
        'name': 'AI_Employee_Linkedin_Publisher',
        'description': 'Publish scheduled LinkedIn posts',
        'script': 'linkedin_mcp_server.py',
        'args': '--publish-scheduled',
        'schedule': 'every_15_min',
        'enabled': True
    },
    'reasoning_loop': {
        'name': 'AI_Employee_Reasoning_Loop',
        'description': 'Process inbox and update plans',
        'script': 'claude_reasoning_loop.py',
        'args': '--analyze --process',
        'schedule': 'every_30_min',
        'enabled': True
    },
    'dashboard_update': {
        'name': 'AI_Employee_Dashboard_Update',
        'description': 'Update the main dashboard',
        'script': 'dashboard_updater.py',
        'args': '',
        'schedule': 'daily_8am',
        'enabled': True
    },
    'weekly_briefing': {
        'name': 'AI_Employee_Weekly_Briefing',
        'description': 'Generate weekly CEO briefing',
        'script': 'briefing_generator.py',
        'args': '--weekly',
        'schedule': 'friday_5pm',
        'enabled': True
    },
    'approval_reminder': {
        'name': 'AI_Employee_Approval_Reminder',
        'description': 'Send reminder for pending approvals',
        'script': 'approval_workflow.py',
        'args': '--list --verbose',
        'schedule': 'daily_9am',
        'enabled': True
    }
}


def log_message(message: str, level: str = "INFO"):
    """Log a message to the log file."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    print(log_entry.strip())


def get_python_path() -> str:
    """Get the current Python executable path."""
    return sys.executable


def get_scheduler_type() -> str:
    """Detect the available scheduler (windows_task or cron)."""
    if sys.platform == 'win32':
        return 'windows_task'
    else:
        return 'cron'


def create_windows_task(task_key: str, task_config: dict) -> bool:
    """Create a Windows Task Scheduler task."""
    python_path = get_python_path()
    script_path = SCRIPTS_PATH / task_config['script']
    
    # Build the command
    command = f'"{python_path}" "{script_path}" {task_config["args"]}'
    
    # Task name
    task_name = task_config['name']
    
    # Determine trigger based on schedule
    trigger = get_windows_trigger(task_config['schedule'])
    
    if not trigger:
        log_message(f"Unknown schedule type: {task_config['schedule']}", "WARNING")
        return False
    
    # Build schtasks command
    schtasks_cmd = f'schtasks /Create /TN "{task_name}" /TR "{command}" {trigger} /RL HIGHEST /F'
    
    try:
        log_message(f"Creating task: {task_name}")
        result = subprocess.run(
            schtasks_cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log_message(f"Task created successfully: {task_name}")
            return True
        else:
            log_message(f"Failed to create task: {result.stderr}", "ERROR")
            return False
            
    except Exception as e:
        log_message(f"Error creating task: {e}", "ERROR")
        return False


def get_windows_trigger(schedule: str) -> str:
    """Get Windows Task Scheduler trigger string for a schedule."""
    now = datetime.now()
    
    schedules = {
        'continuous': '/SC ONCE /ST 00:00 /RU SYSTEM',  # Placeholder - should run as service
        'every_15_min': '/SC MINUTE /MO 15',
        'every_30_min': '/SC MINUTE /MO 30',
        'every_hour': '/SC HOURLY /MO 1',
        'daily_8am': '/SC DAILY /ST 08:00',
        'daily_9am': '/SC DAILY /ST 09:00',
        'daily_6pm': '/SC DAILY /ST 18:00',
        'friday_5pm': '/SC WEEKLY /D FRI /ST 17:00',
        'monday_9am': '/SC WEEKLY /D MON /ST 09:00',
        'startup': '/SC ONSTART'
    }
    
    return schedules.get(schedule)


def delete_windows_task(task_name: str) -> bool:
    """Delete a Windows Task Scheduler task."""
    try:
        cmd = f'schtasks /Delete /TN "{task_name}" /F'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            log_message(f"Task deleted: {task_name}")
            return True
        else:
            log_message(f"Failed to delete task: {result.stderr}", "WARNING")
            return False
            
    except Exception as e:
        log_message(f"Error deleting task: {e}", "ERROR")
        return False


def create_cron_entry(task_key: str, task_config: dict) -> str:
    """Create a cron entry for a task."""
    python_path = get_python_path()
    script_path = SCRIPTS_PATH / task_config['script']
    
    command = f'{python_path} {script_path} {task_config["args"]} >> {LOG_FILE} 2>&1'
    
    # Cron schedule based on schedule type
    cron_schedules = {
        'every_15_min': '*/15 * * * *',
        'every_30_min': '*/30 * * * *',
        'every_hour': '0 * * * *',
        'daily_8am': '0 8 * * *',
        'daily_9am': '0 9 * * *',
        'daily_6pm': '0 18 * * *',
        'friday_5pm': '0 17 * * 5',
        'monday_9am': '0 9 * * 1'
    }
    
    schedule = cron_schedules.get(task_config['schedule'])
    if not schedule:
        return f'# Unsupported schedule: {task_config["schedule"]}'
    
    return f'{schedule} {command}'


def install_tasks(enabled_only: bool = True) -> Dict[str, bool]:
    """Install all scheduled tasks."""
    scheduler_type = get_scheduler_type()
    results = {}
    
    log_message(f"Installing tasks using {scheduler_type} scheduler...")
    
    for task_key, task_config in TASKS.items():
        if enabled_only and not task_config.get('enabled', True):
            log_message(f"Skipping disabled task: {task_key}")
            results[task_key] = 'skipped'
            continue
        
        if scheduler_type == 'windows_task':
            success = create_windows_task(task_key, task_config)
            results[task_key] = 'installed' if success else 'failed'
        else:
            # For cron, we'll create a config file
            results[task_key] = 'configured'
    
    # Save state
    save_state({
        'installed_tasks': list(results.keys()),
        'installed_at': datetime.now().isoformat(),
        'scheduler_type': scheduler_type
    })
    
    return results


def uninstall_tasks() -> Dict[str, bool]:
    """Uninstall all scheduled tasks."""
    scheduler_type = get_scheduler_type()
    results = {}
    
    log_message(f"Uninstalling tasks using {scheduler_type} scheduler...")
    
    for task_key, task_config in TASKS.items():
        if scheduler_type == 'windows_task':
            success = delete_windows_task(task_config['name'])
            results[task_key] = 'uninstalled' if success else 'failed'
        else:
            results[task_key] = 'removed'
    
    # Clear state
    save_state({})
    
    return results


def save_state(state: dict):
    """Save scheduler state to file."""
    with open(SCHEDULE_STATE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)


def load_state() -> dict:
    """Load scheduler state from file."""
    if SCHEDULE_STATE.exists():
        with open(SCHEDULE_STATE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def show_status():
    """Show status of all scheduled tasks."""
    scheduler_type = get_scheduler_type()
    state = load_state()
    
    print(f"\n{'='*70}")
    print(f"AI EMPLOYEE SCHEDULER STATUS")
    print(f"{'='*70}")
    print(f"Scheduler Type: {scheduler_type}")
    print(f"Installed At: {state.get('installed_at', 'Not installed')}")
    print(f"{'='*70}\n")
    
    # Check which tasks are actually registered
    if scheduler_type == 'windows_task':
        try:
            result = subprocess.run('schtasks /Query /FO TABLE', shell=True, 
                                   capture_output=True, text=True)
            registered_tasks = result.stdout if result.returncode == 0 else ""
        except:
            registered_tasks = ""
    else:
        registered_tasks = ""
    
    print(f"{'Task':<25} {'Status':<12} {'Schedule':<20} {'Description'}")
    print("-"*80)
    
    for task_key, task_config in TASKS.items():
        status_icon = "✅" if task_config.get('enabled', True) else "⏸️"
        schedule_display = task_config['schedule'].replace('_', ' ').title()
        
        # Check if actually running
        is_running = task_config['name'] in registered_tasks if registered_tasks else task_config.get('enabled', True)
        status = "Running" if is_running and task_config.get('enabled', True) else "Disabled"
        
        print(f"{task_key:<25} {status:<12} {schedule_display:<20} {task_config['description'][:30]}")
    
    print()


def run_task(task_key: str):
    """Manually run a specific task."""
    if task_key not in TASKS:
        print(f"❌ Unknown task: {task_key}")
        print(f"Available tasks: {', '.join(TASKS.keys())}")
        return
    
    task_config = TASKS[task_key]
    python_path = get_python_path()
    script_path = SCRIPTS_PATH / task_config['script']
    
    command = f'"{python_path}" "{script_path}" {task_config["args"]}'
    
    log_message(f"Manually running task: {task_key}")
    print(f"\n🚀 Running: {task_config['name']}")
    print(f"   Command: {command}")
    print("-"*70 + "\n")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=False, text=True)
        log_message(f"Task completed with return code: {result.returncode}")
    except Exception as e:
        log_message(f"Task failed: {e}", "ERROR")


def list_tasks():
    """List all configured tasks."""
    print(f"\n{'='*70}")
    print("CONFIGURED TASKS")
    print(f"{'='*70}\n")
    
    for task_key, task_config in TASKS.items():
        status = "🟢 Enabled" if task_config.get('enabled', True) else "🔴 Disabled"
        
        print(f"📋 {task_key}")
        print(f"   Name: {task_config['name']}")
        print(f"   Script: {task_config['script']}")
        print(f"   Args: {task_config['args']}")
        print(f"   Schedule: {task_config['schedule']}")
        print(f"   Status: {status}")
        print(f"   Description: {task_config['description']}")
        print()


def generate_cron_file():
    """Generate a cron file for Linux/Mac users."""
    cron_entries = []
    cron_entries.append("# AI Employee Scheduled Tasks")
    cron_entries.append(f"# Generated: {datetime.now().isoformat()}")
    cron_entries.append("")
    
    for task_key, task_config in TASKS.items():
        if task_config.get('enabled', True):
            entry = create_cron_entry(task_key, task_config)
            cron_entries.append(f"# {task_config['description']}")
            cron_entries.append(entry)
            cron_entries.append("")
    
    cron_content = '\n'.join(cron_entries)
    
    output_file = CONFIG_PATH / 'ai_employee_cron.txt'
    output_file.write_text(cron_content, encoding='utf-8')
    
    print(f"\n✅ Cron file generated: {output_file}")
    print("\nTo install, run:")
    print(f"  crontab {output_file}")
    print("\nOr add these entries manually to your crontab:")
    print()
    print(cron_content)


def main():
    parser = argparse.ArgumentParser(description='AI Employee Scheduler')
    parser.add_argument('--install', action='store_true', help='Install scheduled tasks')
    parser.add_argument('--uninstall', action='store_true', help='Remove scheduled tasks')
    parser.add_argument('--status', action='store_true', help='Show task status')
    parser.add_argument('--list', action='store_true', help='List all configured tasks')
    parser.add_argument('--run', type=str, metavar='TASK', help='Run a specific task manually')
    parser.add_argument('--generate-cron', action='store_true', help='Generate cron file for Linux/Mac')
    parser.add_argument('--all', action='store_true', help='Include disabled tasks')
    
    args = parser.parse_args()
    
    if args.install:
        results = install_tasks(enabled_only=not args.all)
        print(f"\n✅ Installation complete!")
        for task, status in results.items():
            print(f"   {task}: {status}")
    elif args.uninstall:
        results = uninstall_tasks()
        print(f"\n✅ Uninstallation complete!")
        for task, status in results.items():
            print(f"   {task}: {status}")
    elif args.status:
        show_status()
    elif args.list:
        list_tasks()
    elif args.run:
        run_task(args.run)
    elif args.generate_cron:
        generate_cron_file()
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python scheduler.py --install")
        print("  python scheduler.py --status")
        print("  python scheduler.py --run reasoning_loop")
        print("  python scheduler.py --uninstall")
        print("  python scheduler.py --generate-cron  # For Linux/Mac")


if __name__ == '__main__':
    main()
