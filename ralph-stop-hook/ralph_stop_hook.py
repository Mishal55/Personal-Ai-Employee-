#!/usr/bin/env python3
"""
Ralph Wiggum Stop-Hook for Claude Code

This script intercepts Claude Code's exit attempts and ensures all tasks
in /Needs_Action are moved to /Done before allowing exit.

Usage:
    python ralph_stop_hook.py [--base-path PATH] [--check-interval SECONDS]

Integration with Claude Code:
    Add to your Claude Code hooks configuration or run as a background watcher.
"""

import os
import sys
import time
import json
import argparse
import io
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ralph_quotes import get_ralph_quote, get_motivational_message, get_ralph_interjection


class RalphStopHook:
    """
    Ralph Wiggum-themed stop-hook that prevents exit until all tasks are done.
    
    Uses file movement as the completion signal:
    - Tasks start in /Needs_Action
    - Tasks moved to /Done when completed
    - Hook blocks exit until /Needs_Action is empty
    """
    
    def __init__(self, base_path: str, needs_action_dir: str = "Needs_Action", 
                 done_dir: str = "Done", log_file: str = None):
        self.base_path = Path(base_path)
        self.needs_action_path = self.base_path / needs_action_dir
        self.done_path = self.base_path / done_dir
        self.log_file = Path(log_file) if log_file else None
        
        # Ensure directories exist
        self.needs_action_path.mkdir(parents=True, exist_ok=True)
        self.done_path.mkdir(parents=True, exist_ok=True)
        
        self.check_count = 0
        self.last_task_count = -1
        
    def log(self, message: str):
        """Log a message to file and/or stdout"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
    
    def get_needs_action_files(self) -> List[Path]:
        """Get all files in Needs_Action directory"""
        if not self.needs_action_path.exists():
            return []
        
        files = []
        for item in self.needs_action_path.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                files.append(item)
        
        return sorted(files, key=lambda x: x.stat().st_mtime)
    
    def get_task_count(self) -> int:
        """Get count of tasks needing action"""
        return len(self.get_needs_action_files())
    
    def get_task_summary(self) -> List[dict]:
        """Get summary of tasks in Needs_Action"""
        files = self.get_needs_action_files()
        tasks = []
        
        for f in files:
            stat = f.stat()
            tasks.append({
                'name': f.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'path': str(f)
            })
        
        return tasks
    
    def check_completion(self) -> Tuple[bool, int, List[dict]]:
        """
        Check if all tasks are complete.
        
        Returns:
            Tuple of (is_complete, task_count, task_summary)
        """
        task_count = self.get_task_count()
        summary = self.get_task_summary()
        is_complete = task_count == 0
        
        return is_complete, task_count, summary
    
    def generate_ralph_message(self, task_count: int, task_summary: List[dict]) -> str:
        """Generate a Ralph Wiggum message based on current state"""
        self.check_count += 1
        
        # Build the message
        lines = []
        
        # Ralph header
        lines.append("")
        lines.append("╔" + "═" * 60 + "╗")
        lines.append("║" + " 🍩 RALPH WIGGUM STOP-HOOK ".center(60) + "║")
        lines.append("╚" + "═" * 60 + "╝")
        lines.append("")
        
        # Ralph's reaction based on count
        if self.check_count == 1:
            lines.append(f"👦 Ralph: \"{get_ralph_quote('concern')}\"")
        elif self.check_count <= 3:
            lines.append(f"👦 Ralph: \"{get_ralph_quote('determination')}\"")
        elif self.check_count <= 5:
            lines.append(f"👦 Ralph: \"{get_ralph_quote('panic')}\"")
        else:
            lines.append(f"👦 Ralph: \"{get_ralph_quote('confusion')}\"")
        
        lines.append("")
        
        # Task status
        lines.append("📊 TASK STATUS:")
        lines.append(f"   Tasks in Needs_Action: {task_count}")
        lines.append(f"   Checks performed: {self.check_count}")
        lines.append("")
        
        # List tasks if any remain
        if task_count > 0:
            lines.append("📋 REMAINING TASKS:")
            for i, task in enumerate(task_summary[:10], 1):  # Show max 10
                lines.append(f"   {i}. {task['name']}")
            
            if task_count > 10:
                lines.append(f"   ... and {task_count - 10} more")
            
            lines.append("")
            
            # Motivational message
            lines.append(f"💪 {get_motivational_message(task_count)}")
            lines.append("")
            
            # Ralph wisdom
            if self.check_count % 3 == 0:
                lines.append(f"🧠 Ralph's Wisdom: \"{get_ralph_quote('wisdom')}\"")
                lines.append("")
        else:
            lines.append(f"🎉 {get_ralph_quote('celebration')}")
            lines.append("")
        
        # Instructions
        lines.append("📝 TO COMPLETE:")
        lines.append("   Move all files from /Needs_Action to /Done")
        lines.append("   Ralph will let you exit when the folder is empty!")
        lines.append("")
        
        # Random interjection
        if self.check_count % 2 == 0:
            lines.append(f"🦋 Ralph: \"{get_ralph_interjection()}\"")
            lines.append("")
        
        lines.append("═" * 62)
        
        return '\n'.join(lines)
    
    def run_check(self) -> bool:
        """
        Run a single completion check.
        
        Returns:
            True if can exit (all tasks done), False if must continue
        """
        is_complete, task_count, summary = self.check_completion()
        
        # Generate and display Ralph's message
        message = self.generate_ralph_message(task_count, summary)
        self.log(message)
        
        # Track changes
        if task_count != self.last_task_count:
            if task_count < self.last_task_count and self.last_task_count != -1:
                moved = self.last_task_count - task_count
                self.log(f"✅ {moved} task(s) moved to Done! Great job!")
            self.last_task_count = task_count
        
        return is_complete
    
    def wait_for_completion(self, poll_interval: float = 2.0) -> bool:
        """
        Wait until all tasks are complete, polling periodically.
        
        Args:
            poll_interval: Seconds between checks
        
        Returns:
            True when all tasks are complete
        """
        self.log("🚀 Ralph Wiggum Stop-Hook activated!")
        self.log("📁 Monitoring Needs_Action directory...")
        
        while True:
            is_complete = self.run_check()
            
            if is_complete:
                self.log("")
                self.log("🎊 ALL TASKS COMPLETE! Ralph says you can exit now!")
                self.log("")
                return True
            
            # Wait before next check
            time.sleep(poll_interval)


def create_hook_script(output_path: str, base_path: str):
    """Create a standalone hook script for integration"""
    
    script_content = f'''#!/usr/bin/env python3
"""
Auto-generated Ralph Wiggum Stop-Hook
Base Path: {base_path}
"""

import sys
from pathlib import Path

# Add the ralph-stop-hook src to path
sys.path.insert(0, r"{Path(__file__).parent / 'src'}")

from ralph_stop_hook import RalphStopHook

if __name__ == "__main__":
    hook = RalphStopHook(
        base_path=r"{base_path}",
        needs_action_dir="Needs_Action",
        done_dir="Done",
        log_file=r"{Path(base_path) / 'logs' / 'ralph_hook.log'}"
    )
    
    try:
        hook.wait_for_completion(poll_interval=2.0)
        sys.exit(0)
    except KeyboardInterrupt:
        print("\\n👦 Ralph: \\"Me know you tried! But tasks still need doing!\\"")
        sys.exit(1)
'''
    
    output = Path(output_path)
    output.write_text(script_content, encoding='utf-8')
    output.chmod(0o755)
    
    return str(output)


def main():
    parser = argparse.ArgumentParser(
        description='Ralph Wiggum Stop-Hook for Claude Code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python ralph_stop_hook.py --base-path "D:/Personal Ai Employee"
  python ralph_stop_hook.py -b . --interval 5
  python ralph_stop_hook.py --create-hook ./my_hook.py

Ralph says: "Me love helping you finish tasks!"
        '''
    )
    
    parser.add_argument(
        '--base-path', '-b',
        type=str,
        default='.',
        help='Base path containing Needs_Action and Done directories'
    )
    
    parser.add_argument(
        '--interval', '-i',
        type=float,
        default=2.0,
        help='Check interval in seconds (default: 2.0)'
    )
    
    parser.add_argument(
        '--log-file', '-l',
        type=str,
        default=None,
        help='Log file path'
    )
    
    parser.add_argument(
        '--create-hook', '-c',
        type=str,
        default=None,
        help='Create a standalone hook script at the specified path'
    )
    
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Run a single check and exit (don\'t wait)'
    )
    
    args = parser.parse_args()
    
    # Handle create-hook mode
    if args.create_hook:
        script_path = create_hook_script(args.create_hook, args.base_path)
        print(f"✅ Hook script created: {script_path}")
        return 0
    
    # Create and run the hook
    hook = RalphStopHook(
        base_path=args.base_path,
        log_file=args.log_file
    )
    
    if args.check_only:
        # Single check mode
        is_complete, count, summary = hook.check_completion()
        print(hook.generate_ralph_message(count, summary))
        return 0 if is_complete else 1
    
    # Continuous monitoring mode
    try:
        hook.wait_for_completion(poll_interval=args.interval)
        return 0
    except KeyboardInterrupt:
        print("\n👦 Ralph: \"Me know you tried! But tasks still need doing!\"")
        return 1


if __name__ == '__main__':
    sys.exit(main())
