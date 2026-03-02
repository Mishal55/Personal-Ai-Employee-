# AI Employee Silver Tier - Upgrade Guide

> **Version:** 0.2 (Silver Tier)  
> **Upgrade Date:** 2026-02-25  
> **Previous Version:** 0.1 (Bronze Tier)

---

## 🎯 What's New in Silver Tier

Silver Tier adds **autonomous monitoring**, **social media automation**, **structured planning**, and **scheduled execution** to your AI Employee:

| Feature | Bronze | Silver |
|---------|--------|--------|
| Manual Task Processing | ✅ | ✅ |
| Human-in-the-Loop Approval | ✅ | ✅ |
| **WhatsApp Monitoring** | ❌ | ✅ |
| **LinkedIn Auto-Posting** | ❌ | ✅ |
| **Claude Reasoning Loop** | ❌ | ✅ |
| **Plan.md Generation** | ❌ | ✅ |
| **Task Scheduler** | ❌ | ✅ |
| **Dashboard Auto-Update** | ❌ | ✅ |
| **Weekly Briefings** | ❌ | ✅ |

---

## 📁 New Folder Structure

```
AI_Employee_Vault/
├── watchers/
│   ├── whatsapp/          # WhatsApp watcher state & logs
│   └── linkedin/          # LinkedIn posts (drafts/scheduled/published)
├── Plans/                 # Generated task plans with checkboxes
├── Pending_Approval/      # Items awaiting human approval
├── Approved/              # Approved items ready for execution
├── Rejected/              # Rejected items with reasons
├── Briefings/             # Weekly/Monthly CEO briefings
└── Scheduler/             # Task scheduler configuration
```

---

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
cd "D:\Personal Ai Employee"
pip install -r requirements.txt
playwright install chromium
```

### Step 2: Test Individual Components

```bash
# Test WhatsApp watcher (single check)
python scripts/whatsapp_watcher.py --check

# Test reasoning loop
python scripts/claude_reasoning_loop.py --analyze

# Test approval workflow
python scripts/approval_workflow.py --list

# Test dashboard update
python scripts/dashboard_updater.py
```

### Step 3: Install Scheduled Tasks

```bash
# Windows - Install all scheduled tasks
python scripts/scheduler.py --install

# Check status
python scripts/scheduler.py --status
```

---

## 📋 Feature Documentation

### 1. WhatsApp Watcher

**Purpose:** Monitor WhatsApp Web for new messages and create action items automatically.

**How it works:**
1. Uses Playwright to automate WhatsApp Web
2. Checks for new messages every 2 minutes (configurable)
3. Creates inbox items in `AI_Employee_Vault/Inbox/`
4. Tracks processed messages to avoid duplicates

**Usage:**
```bash
# Continuous monitoring
python scripts/whatsapp_watcher.py --watch --interval 120

# Single check
python scripts/whatsapp_watcher.py --check

# Run for 1 hour then stop
python scripts/whatsapp_watcher.py --watch --max-duration 3600
```

**First-Time Setup:**
1. Run the watcher
2. Scan the QR code with your WhatsApp mobile app
3. Session is saved for future runs

**Files Created:**
- `AI_Employee_Vault/watchers/whatsapp/state.json` - Session state
- `AI_Employee_Vault/Logs/whatsapp_watcher.log` - Activity log
- `AI_Employee_Vault/Inbox/WHATSAPP_{contact}_{timestamp}.md` - New messages

---

### 2. LinkedIn Auto-Posting MCP Server

**Purpose:** Create, schedule, and publish LinkedIn posts with human approval workflow.

**How it works:**
1. Create post drafts via MCP tools
2. Submit for human approval
3. Schedule approved posts
4. Publish at scheduled times

**MCP Tools Available:**
| Tool | Description |
|------|-------------|
| `create_linkedin_post` | Create a new draft post |
| `request_linkedin_approval` | Submit draft for approval |
| `schedule_linkedin_post` | Schedule an approved post |
| `publish_linkedin_post` | Publish immediately |
| `list_linkedin_posts` | List all posts by status |
| `cancel_scheduled_post` | Cancel a scheduled post |

**Usage via MCP Client:**
```bash
# Connect to LinkedIn MCP server
python .qwen/skills/browsing-with-playwright/scripts/mcp-client.py \
  --stdio "python scripts/linkedin_mcp_server.py" list

# Create a post
python .qwen/skills/browsing-with-playwright/scripts/mcp-client.py \
  --stdio "python scripts/linkedin_mcp_server.py" call \
  --tool create_linkedin_post \
  --params '{"content": "Excited to share...", "hashtags": ["AI", "Automation"]}'
```

**Approval Workflow:**
1. Draft created → `watchers/linkedin/drafts/`
2. Submit for approval → `Pending_Approval/`
3. Human approves → `Approved/`
4. Schedule → `watchers/linkedin/scheduled/`
5. Published → `watchers/linkedin/published/`

---

### 3. Claude Reasoning Loop

**Purpose:** Automatically analyze incoming tasks and generate structured execution plans.

**How it works:**
1. Scans `Inbox/` and `Needs_Action/` for new items
2. Analyzes content to determine task type
3. Generates action items based on patterns
4. Creates `Plan.md` files with checkboxes
5. Tracks progress and moves completed plans to `Done/`

**Usage:**
```bash
# Analyze inbox and create plans
python scripts/claude_reasoning_loop.py --analyze

# Process plans (check completion, move to Done)
python scripts/claude_reasoning_loop.py --process

# Show status of all plans
python scripts/claude_reasoning_loop.py --status
```

**Plan.md Structure:**
```markdown
---
plan_id: PLAN_example_20260225
status: draft
total_actions: 6
completed_actions: 0
---

# Task Plan: example.md

## Action Plan
- [ ] **ACT_001** [analysis] Analyze task requirements
- [ ] **ACT_002** [verification] Verify details
- [ ] **ACT_003** [approval] HITL: Requires approval
...
```

**Task Categories Recognized:**
- Invoice/Payment → Financial workflow
- Email/Reply → Communication workflow
- WhatsApp/Message → Communication workflow
- File/Document → Processing workflow
- Schedule/Meeting → Scheduling workflow
- LinkedIn/Post → Marketing workflow

---

### 4. Human-in-the-Loop Approval Workflow

**Purpose:** Manage pending approvals with full audit trail.

**Usage:**
```bash
# List pending approvals
python scripts/approval_workflow.py --list

# Show details of specific item
python scripts/approval_workflow.py --show APPROVAL_payment_2026-02-25.md

# Approve with notes
python scripts/approval_workflow.py --approve APPROVAL_payment_2026-02-25.md \
  --notes "Verified against invoice #12345"

# Reject with reason
python scripts/approval_workflow.py --reject APPROVAL_email_2026-02-25.md \
  --reason "Content needs revision"

# Interactive batch processing
python scripts/approval_workflow.py --batch

# View approval log
python scripts/approval_workflow.py --log
```

**Approval States:**
1. `pending_approval` → Awaiting human review
2. `approved` → Ready for execution
3. `rejected` → Returned with reasons
4. `completed` → Executed and archived

**Audit Trail:**
All approvals/rejections logged to `AI_Employee_Vault/Logs/approvals.jsonl`

---

### 5. Task Scheduler

**Purpose:** Run AI Employee tasks automatically on schedule.

**Configured Tasks:**
| Task | Schedule | Description |
|------|----------|-------------|
| `whatsapp_watcher` | Continuous | Monitor WhatsApp |
| `linkedin_publisher` | Every 15 min | Publish scheduled posts |
| `reasoning_loop` | Every 30 min | Process inbox |
| `dashboard_update` | Daily 8am | Update dashboard |
| `weekly_briefing` | Friday 5pm | Generate briefing |
| `approval_reminder` | Daily 9am | Reminder for pending |

**Usage:**
```bash
# Install all scheduled tasks (Windows Task Scheduler)
python scripts/scheduler.py --install

# Check status
python scripts/scheduler.py --status

# List all configured tasks
python scripts/scheduler.py --list

# Run a task manually
python scripts/scheduler.py --run reasoning_loop

# Uninstall all tasks
python scripts/scheduler.py --uninstall

# Generate cron file (Linux/Mac)
python scripts/scheduler.py --generate-cron
```

**Windows Task Scheduler:**
Tasks are registered in Windows Task Scheduler with names like:
- `AI_Employee_WhatsApp_Watcher`
- `AI_Employee_Reasoning_Loop`
- `AI_Employee_Dashboard_Update`

---

## 📊 Dashboard & Briefings

### Dashboard Auto-Update

The dashboard is automatically updated daily showing:
- Pending tasks count
- Awaiting approval count
- Tasks completed today/this week
- Recent activity log

```bash
# Manual update
python scripts/dashboard_updater.py
```

### Weekly Briefings

Every Friday at 5pm, a weekly briefing is generated:

```bash
# Manual generation
python scripts/briefing_generator.py --weekly
```

Briefings saved to `AI_Employee_Vault/Briefings/`

---

## 🔧 Configuration

### Environment Variables (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_VAULT_PATH` | `D:\Personal Ai Employee\AI_Employee_Vault` | Vault location |
| `AI_SCRIPTS_PATH` | `D:\Personal Ai Employee\scripts` | Scripts location |
| `AI_CONFIG_PATH` | `D:\Personal Ai Employee\config` | Config files |

### WhatsApp Watcher Settings

Edit `scripts/whatsapp_watcher.py`:
```python
CHECK_INTERVAL = 120  # Seconds between checks
MAX_DURATION = 0      # 0 = run forever
```

### Scheduler Settings

Edit `scripts/scheduler.py` TASKS dictionary to modify schedules.

---

## 🚨 Troubleshooting

### WhatsApp Watcher Issues

**Problem:** QR code doesn't appear
- **Solution:** Clear browser cache, restart watcher

**Problem:** Session expires frequently
- **Solution:** Keep WhatsApp mobile app connected to internet

**Problem:** Messages not detected
- **Solution:** Ensure WhatsApp Web is fully loaded before monitoring starts

### LinkedIn MCP Issues

**Problem:** MCP server not responding
- **Solution:** Check `AI_Employee_Vault/Logs/linkedin_mcp.log`

**Problem:** Posts not moving through workflow
- **Solution:** Verify file permissions in vault folders

### Scheduler Issues

**Problem:** Tasks not running
- **Solution:** Check Windows Task Scheduler library for errors

**Problem:** Python not found
- **Solution:** Ensure Python is in PATH or use full path in task configuration

---

## 📈 Upgrade Path to Gold Tier

Future Gold Tier features (planned):
- [ ] Email integration (IMAP/SMTP)
- [ ] Calendar integration
- [ ] Voice command support
- [ ] Advanced analytics dashboard
- [ ] Multi-user support
- [ ] API endpoints for external integration

---

## 📝 Command Reference

### Quick Commands

```bash
# Full system check
python scripts/claude_reasoning_loop.py --status
python scripts/approval_workflow.py --list
python scripts/scheduler.py --status

# Process everything
python scripts/claude_reasoning_loop.py --analyze
python scripts/claude_reasoning_loop.py --process
python scripts/dashboard_updater.py

# Approval workflow
python scripts/approval_workflow.py --batch
```

### Log Locations

| Log | Location |
|-----|----------|
| WhatsApp | `AI_Employee_Vault/Logs/whatsapp_watcher.log` |
| LinkedIn | `AI_Employee_Vault/Logs/linkedin_mcp.log` |
| Reasoning | `AI_Employee_Vault/Logs/reasoning_loop.log` |
| Approval | `AI_Employee_Vault/Logs/approval_workflow.log` |
| Scheduler | `AI_Employee_Vault/Logs/scheduler.log` |
| Approvals (JSONL) | `AI_Employee_Vault/Logs/approvals.jsonl` |

---

*AI Employee Silver Tier v0.2*  
*Upgrade completed: 2026-02-25*
