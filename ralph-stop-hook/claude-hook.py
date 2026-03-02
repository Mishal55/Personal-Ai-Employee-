#!/usr/bin/env python3
"""
Claude Code Integration - Ralph Wiggum Stop-Hook

This script can be called by Claude Code before exiting to ensure
all tasks are complete.

Usage in Claude Code:
    /hook ralph_stop

Or add to your Claude Code configuration:
    hooks:
      pre-exit: python /path/to/ralph-claude-hook.py
"""

import sys
import os
from pathlib import Path

# Find the ralph-stop-hook directory
script_dir = Path(__file__).parent
src_dir = script_dir / 'src'

# Add to path
sys.path.insert(0, str(src_dir))

from ralph_stop_hook import RalphStopHook


def check_and_prompt():
    """
    Check if tasks remain and prompt Claude Code to continue working.
    
    Returns:
        0 if all tasks complete (can exit)
        1 if tasks remain (should continue working)
    """
    # Determine base path - look for common patterns
    possible_paths = [
        Path.cwd(),
        Path.cwd().parent,
        Path.home() / 'Personal Ai Employee',
        Path('D:/Personal Ai Employee'),
    ]
    
    base_path = None
    for p in possible_paths:
        if (p / 'Needs_Action').exists():
            base_path = p
            break
    
    if not base_path:
        base_path = Path.cwd()
    
    hook = RalphStopHook(base_path=str(base_path))
    is_complete, count, summary = hook.check_completion()
    
    # Print Ralph's message
    print(hook.generate_ralph_message(count, summary))
    
    if is_complete:
        print("\n✅ Ralph says you're free to go!")
        return 0
    else:
        print("\n👦 Ralph: \"Me can't let you stop yet! There's still work to do!\"")
        print("\n💡 Tip: Move files from Needs_Action to Done when you complete them.")
        return 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Ralph Wiggum Claude Code Hook')
    parser.add_argument('--base-path', '-b', type=str, default=None,
                       help='Base path to check')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output')
    
    args = parser.parse_args()
    
    if args.base_path:
        hook = RalphStopHook(base_path=args.base_path)
    else:
        hook = RalphStopHook(base_path=str(Path.cwd()))
    
    is_complete, count, summary = hook.check_completion()
    
    if args.verbose:
        print(hook.generate_ralph_message(count, summary))
    
    if is_complete:
        if not args.verbose:
            print("🎉 Ralph: \"All done! You can exit now!\"")
        return 0
    else:
        if not args.verbose:
            print(f"👦 Ralph: \"Wait! {count} task(s) still need action!\"")
            for task in summary[:5]:
                print(f"   - {task['name']}")
            if count > 5:
                print(f"   ...and {count - 5} more")
        return 1


if __name__ == '__main__':
    sys.exit(main())
