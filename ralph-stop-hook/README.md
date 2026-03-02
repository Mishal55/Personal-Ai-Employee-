# 🍩 Ralph Wiggum Stop-Hook for Claude Code

> *"Me fail completion? That's unpossible!"*

A playful stop-hook that prevents Claude Code from exiting until all tasks in `/Needs_Action` are moved to `/Done`. Features everyone's favorite Springfield Elementary student providing motivation, concern, and occasional panic.

## Features

- 🎯 **File-based completion signal** - Uses file movement as the task completion indicator
- 👦 **Ralph Wiggum commentary** - 50+ quotes across multiple emotional states
- 📊 **Real-time monitoring** - Polls the Needs_Action directory continuously
- 📝 **Task summaries** - Shows remaining tasks with timestamps
- 🎊 **Celebration mode** - Special messages when all tasks complete
- 🔧 **Flexible integration** - CLI, background process, or embedded hook

## Installation

```bash
cd ralph-stop-hook
# No dependencies required - uses Python standard library!
```

## Project Structure

```
ralph-stop-hook/
├── ralph_stop_hook.py      # Main script
├── src/
│   ├── __init__.py
│   └── ralph_quotes.py     # Ralph Wiggum quote library
├── Needs_Action/           # Tasks that need attention
├── Done/                   # Completed tasks
├── logs/                   # Hook activity logs
└── README.md
```

## Usage

### Basic Usage

```bash
# Run with default settings (checks current directory)
python ralph_stop_hook.py

# Specify base path
python ralph_stop_hook.py --base-path "D:/Personal Ai Employee"

# Custom check interval
python ralph_stop_hook.py --interval 5

# Single check (don't wait)
python ralph_stop_hook.py --check-only
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--base-path`, `-b` | Base path containing Needs_Action and Done directories |
| `--interval`, `-i` | Check interval in seconds (default: 2.0) |
| `--log-file`, `-l` | Log file path |
| `--create-hook`, `-c` | Create standalone hook script |
| `--check-only` | Run single check and exit |

### Example Output

```
╔════════════════════════════════════════════════════════════════╗
║                    🍩 RALPH WIGGUM STOP-HOOK                   ║
╚════════════════════════════════════════════════════════════════╝

👦 Ralph: "Uh oh... me see files that need attention."

📊 TASK STATUS:
   Tasks in Needs_Action: 3
   Checks performed: 1

📋 REMAINING TASKS:
   1. fix_bug_123.md
   2. update_docs.md
   3. review_pr.md

💪 Ralph: "Me not letting you quit! We gotta finish!" 3 tasks to go!

📝 TO COMPLETE:
   Move all files from /Needs_Action to /Done
   Ralph will let you exit when the folder is empty!

══════════════════════════════════════════════════════════════════
```

## Integration with Claude Code

### Method 1: Background Process

Start the hook as a background process when working:

```bash
# Start hook in background
python ralph_stop_hook.py --base-path "D:/Personal Ai Employee" &

# Now use Claude Code normally
claude

# Ralph will keep checking until tasks are done
```

### Method 2: Pre-commit Hook

Add to your git pre-commit hook:

```bash
#!/bin/bash
# .git/hooks/pre-commit

python ralph_stop_hook.py --check-only --base-path "."
if [ $? -ne 0 ]; then
    echo "👦 Ralph: Please move all tasks to Done before committing!"
    exit 1
fi
```

### Method 3: Create Standalone Hook

```bash
python ralph_stop_hook.py --create-hook ./my_project_hook.py --base-path "."

# Then use the generated script
python my_project_hook.py
```

### Method 4: Claude Code Hooks Directory

Create a hooks configuration:

```bash
# Create hooks directory
mkdir -p .claude/hooks

# Create stop hook script
cat > .claude/hooks/ralph-stop.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/path/to/ralph-stop-hook/src')
from ralph_stop_hook import RalphStopHook

hook = RalphStopHook(base_path='.')
if not hook.run_check():
    print("\n👦 Ralph: \"Me can't let you stop yet!\"")
    sys.exit(1)
EOF

chmod +x .claude/hooks/ralph-stop.py
```

## Ralph's Emotional States

Ralph reacts differently based on how long you've been working:

| Check Count | Ralph's State | Example Quote |
|-------------|---------------|---------------|
| 1 | Concern | "Me think there's still stuff in Needs_Action..." |
| 2-3 | Determination | "Ralph Wiggum say: NO STOPPING UNTIL DONE!" |
| 4-5 | Panic | "I'm in danger! ...of not finishing our tasks!" |
| 6+ | Confusion | "Me confused... why we stopping when work not done?" |
| Every 3rd | Wisdom | "Me dad say: 'A job unfinished is like a donut with no hole.'" |
| 0 tasks | Celebration | "YAY! All done! Me so proud!" |

## Workflow Example

1. **Create task files** in `Needs_Action/`:
   ```bash
   echo "Fix the login bug" > Needs_Action/fix_login_bug.md
   echo "Update documentation" > Needs_Action/update_docs.md
   ```

2. **Start the hook**:
   ```bash
   python ralph_stop_hook.py
   ```

3. **Work on tasks** - Ralph monitors in the background

4. **Move completed tasks**:
   ```bash
   mv Needs_Action/fix_login_bug.md Done/
   ```

5. **Ralph notices progress**:
   ```
   ✅ 1 task(s) moved to Done! Great job!
   ```

6. **Complete all tasks** - Ralph celebrates and allows exit

## Quote Categories

The hook includes 50+ Ralph Wiggum quotes across 8 categories:

- 🎯 **encouragement** - Positive reinforcement
- ⚠️ **concern** - Initial warnings
- 😱 **panic** - Escalating urgency
- 🤔 **confusion** - Questioning your choices
- 💪 **determination** - Motivational push
- 🎉 **celebration** - Victory messages
- 🧠 **wisdom** - Ralph's life lessons
- 🦋 **random** - Classic Ralph randomness

## Logging

Enable logging to track hook activity:

```bash
python ralph_stop_hook.py --log-file logs/ralph_hook.log
```

Log format:
```
[2026-02-27 09:15:32] 🚀 Ralph Wiggum Stop-Hook activated!
[2026-02-27 09:15:32] 📁 Monitoring Needs_Action directory...
[2026-02-27 09:15:35] ✅ 1 task(s) moved to Done! Great job!
```

## Customization

### Add Your Own Quotes

Edit `src/ralph_quotes.py`:

```python
RALPH_QUOTES["custom"] = [
    "Your custom Ralph quote here!",
    "Another quote!",
]
```

### Change Polling Interval

```bash
# Check every 5 seconds instead of 2
python ralph_stop_hook.py --interval 5
```

### Use Different Directory Names

```python
hook = RalphStopHook(
    base_path=".",
    needs_action_dir="ToDo",
    done_dir="Completed"
)
```

## Troubleshooting

**"Ralph won't stop talking!"**
- That's... kind of the point? Move your tasks to Done!

**"Hook not detecting file moves"**
- Ensure files are actually moved (not copied)
- Check file permissions
- Try increasing poll interval

**"Too many Ralph quotes!"**
- There's no such thing. But you can edit `src/ralph_quotes.py`

## License

MIT - Just like Ralph's understanding of advanced mathematics.

---

*"Me love the task movement!"* - Ralph Wiggum, probably
