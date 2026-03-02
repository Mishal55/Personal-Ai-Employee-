# AI Employee Gold Tier - Complete Upgrade Guide

> **Version:** 0.3 (Gold Tier)  
> **Upgrade Date:** 2026-02-25  
> **Previous Version:** 0.2 (Silver Tier)

---

## 🏆 What's New in Gold Tier

Gold Tier adds **enterprise integrations**, **multi-platform social media**, **autonomous reasoning**, and **comprehensive CEO briefings**:

| Feature | Bronze | Silver | Gold |
|---------|--------|--------|------|
| Manual Task Processing | ✅ | ✅ | ✅ |
| Human-in-the-Loop Approval | ✅ | ✅ | ✅ |
| WhatsApp Monitoring | ❌ | ✅ | ✅ |
| LinkedIn Auto-Posting | ❌ | ✅ | ✅ |
| Claude Reasoning Loop | ❌ | ✅ | ✅ |
| **Odoo Accounting** | ❌ | ❌ | ✅ |
| **Multi-Platform Social** | ❌ | ❌ | ✅ |
| **Ralph Wiggum Loop** | ❌ | ❌ | ✅ |
| **CEO Briefings** | ❌ | ❌ | ✅ |
| **MCP Gateway** | ❌ | ❌ | ✅ |

---

## 🎯 Gold Tier Capabilities

### 1. Enterprise Accounting (Odoo)
- Create and manage invoices
- Register payments
- Financial reports (P&L, Balance Sheet)
- Customer/Vendor management
- Journal entries

### 2. Multi-Platform Social Media
- Facebook page posts
- Instagram posts with hashtags
- Twitter tweets (280 char optimized)
- Cross-platform posting
- Content summarization

### 3. Ralph Wiggum Autonomous Loop
- Self-correcting task execution
- Automatic retry logic
- Smart escalation
- Continuous improvement

### 4. Enhanced CEO Briefings
- Revenue tracking
- Bottleneck analysis
- Proactive suggestions
- Weekly/Monthly reports

### 5. Unified MCP Gateway
- Single connection point
- Multiple server routing
- Tool aggregation

---

## 📁 Complete Folder Structure

```
D:\Personal Ai Employee\
├── scripts/
│   ├── whatsapp_watcher.py         # Silver Tier
│   ├── linkedin_mcp_server.py      # Silver Tier
│   ├── claude_reasoning_loop.py    # Silver Tier
│   ├── approval_workflow.py        # Silver Tier
│   ├── scheduler.py                # Silver Tier
│   ├── dashboard_updater.py        # Silver Tier
│   ├── briefing_generator.py       # Silver Tier
│   ├── ralph_wiggum_loop.py        # Gold Tier ⭐
│   ├── ceo_briefing_generator.py   # Gold Tier ⭐
│   └── mcp_gateway.py              # Gold Tier ⭐
├── mcp-servers/
│   ├── odoo_accounting_mcp.py      # Gold Tier ⭐
│   └── social_media_mcp.py         # Gold Tier ⭐
├── config/
│   └── scheduler_state.json
└── AI_Employee_Vault/
    ├── Dashboard.md
    ├── Company_Handbook.md
    ├── Business_Goals.md
    ├── Inbox/
    ├── Needs_Action/
    ├── Plans/
    ├── Pending_Approval/
    ├── Approved/
    ├── Rejected/
    ├── Done/
    ├── Briefings/
    │   ├── CEO/                    # Gold Tier ⭐
    │   └── weekly_*.md
    ├── Accounting/
    │   └── Odoo/                   # Gold Tier ⭐
    ├── Logs/
    ├── watchers/
    │   ├── whatsapp/
    │   ├── linkedin/
    │   ├── facebook/               # Gold Tier ⭐
    │   ├── instagram/              # Gold Tier ⭐
    │   └── twitter/                # Gold Tier ⭐
    └── Scheduler/
```

---

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
cd "D:\Personal Ai Employee"
pip install -r requirements.txt
playwright install chromium
```

### Step 2: Configure Odoo (Optional)

Create `.env` file in project root:

```bash
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=your_password
ODOO_COMPANY_ID=1
```

### Step 3: Configure Social Media (Optional)

Add to `.env`:

```bash
# Facebook
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_ACCESS_TOKEN=your_token

# Instagram
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_account_id
INSTAGRAM_ACCESS_TOKEN=your_token

# Twitter
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_SECRET=your_secret
```

### Step 4: Test Gold Tier Components

```bash
# Test Ralph Wiggum Loop
python scripts\ralph_wiggum_loop.py --status

# Test CEO Briefing Generator
python scripts\ceo_briefing_generator.py --weekly --preview

# Test MCP Gateway
python scripts\mcp_gateway.py --list-servers

# Test Odoo MCP (if configured)
python mcp-servers\odoo_accounting_mcp.py --cli

# Test Social Media MCP
python mcp-servers\social_media_mcp.py --cli
```

### Step 5: Install Scheduled Tasks

```bash
# Update scheduler with Gold Tier tasks
python scripts\scheduler.py --install
```

---

## 📋 Gold Tier Commands

### Ralph Wiggum Autonomous Loop

```bash
# Run one complete loop
python scripts\ralph_wiggum_loop.py --run

# Run continuously (every 5 minutes)
python scripts\ralph_wiggum_loop.py --continuous --interval 300

# Check status
python scripts\ralph_wiggum_loop.py --status
```

### CEO Briefing Generator

```bash
# Generate weekly briefing
python scripts\ceo_briefing_generator.py --weekly

# Generate monthly briefing
python scripts\ceo_briefing_generator.py --monthly

# Preview without saving
python scripts\ceo_briefing_generator.py --weekly --preview
```

### MCP Gateway

```bash
# List available servers
python scripts\mcp_gateway.py --list-servers

# Run gateway with specific servers
python scripts\mcp_gateway.py --servers odoo_accounting,social_media

# Run with all servers (default)
python scripts\mcp_gateway.py
```

### Odoo Accounting MCP

```bash
# CLI mode
python mcp-servers\odoo_accounting_mcp.py --cli

# MCP stdio mode
python mcp-servers\odoo_accounting_mcp.py

# Via MCP client
python .qwen\skills\browsing-with-playwright\scripts\mcp-client.py ^
  --stdio "python mcp-servers\odoo_accounting_mcp.py" list
```

### Social Media MCP

```bash
# CLI mode
python mcp-servers\social_media_mcp.py --cli

# Create Facebook post
python .qwen\skills\browsing-with-playwright\scripts\mcp-client.py ^
  --stdio "python mcp-servers\social_media_mcp.py" call ^
  --tool create_facebook_post ^
  --params '{"content": "Hello from AI Employee Gold Tier!"}'

# Cross-post to multiple platforms
python .qwen\skills\browsing-with-playwright\scripts\mcp-client.py ^
  --stdio "python mcp-servers\social_media_mcp.py" call ^
  --tool cross_post ^
  --params '{"content": "Big announcement!", "platforms": ["facebook", "twitter", "linkedin"]}'
```

---

## 🔧 MCP Server Reference

### Odoo Accounting Tools

| Tool | Description | HITL Required |
|------|-------------|---------------|
| `create_invoice` | Create customer invoice | ✅ Yes |
| `list_invoices` | List invoices with filters | ❌ No |
| `validate_invoice` | Validate draft invoice | ✅ Yes |
| `register_payment` | Record payment | ✅ Yes |
| `list_customers` | List all customers | ❌ No |
| `list_vendors` | List all vendors | ❌ No |
| `get_account_report` | Get P&L, Balance Sheet | ❌ No |
| `create_journal_entry` | Manual journal entry | ✅ Yes |

### Social Media Tools

| Tool | Description | HITL Required |
|------|-------------|---------------|
| `create_facebook_post` | Create FB post | ✅ Yes |
| `create_instagram_post` | Create IG post | ✅ Yes |
| `create_twitter_tweet` | Create tweet | ✅ Yes |
| `schedule_post` | Schedule for publishing | ✅ Yes |
| `publish_post` | Publish immediately | ✅ Yes |
| `list_posts` | List all posts | ❌ No |
| `cross_post` | Post to multiple platforms | ✅ Yes |
| `generate_content_summary` | Optimize content | ❌ No |
| `cancel_post` | Cancel scheduled post | ✅ Yes |

---

## 🤖 Ralph Wiggum Loop Architecture

### OODAL Cycle

```
┌─────────────────────────────────────────────────────────┐
│                    RALPH WIGGUM LOOP                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. OBSERVE  →  Scan inbox, plans, approvals            │
│       ↓                                                  │
│  2. ORIENT   →  Prioritize tasks by urgency             │
│       ↓                                                  │
│  3. DECIDE   →  Create action plans                     │
│       ↓                                                  │
│  4. ACT      →  Execute with retry logic                │
│       ↓                                                  │
│  5. LEARN    →  Log outcomes, update stats              │
│       ↓                                                  │
│  (Repeat)                                                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Retry Logic

```
Task Fails
    ↓
Retry 1 (wait 1s)
    ↓
Retry 2 (wait 2s)
    ↓
Retry 3 (wait 3s)
    ↓
Escalate to Human → Create ESCALATION_*.md in Needs_Action/
```

### Priority Rules

1. **Priority 1:** Blocked tasks needing unblocking
2. **Priority 2:** Due scheduled posts
3. **Priority 3:** Plans in progress
4. **Priority 4:** New inbox items
5. **Priority 5:** Needs action items

---

## 📊 CEO Briefing Components

### Weekly Briefing Sections

1. **Executive Summary** - Key metrics at a glance
2. **Financial Performance** - Revenue, expenses, net income
3. **Activity Metrics** - Tasks, loops, approvals
4. **Bottleneck Analysis** - Current blockers and issues
5. **Proactive Suggestions** - AI-generated recommendations
6. **Next Week Priorities** - Auto-generated action items

### Bottleneck Detection

The system automatically detects:

| Bottleneck | Threshold | Severity |
|------------|-----------|----------|
| Approval backlog | > 10 items | High |
| Approval backlog | > 5 items | Medium |
| Inbox backlog | > 20 items | High |
| Action backlog | > 10 items | Medium |
| Frequent escalations | > 3/week | High |
| Stale plans | > 7 days | Medium |

---

## 🔐 Security & Compliance

### Audit Trails

All Gold Tier actions are logged:

| Log File | Contents |
|----------|----------|
| `Logs/odoo_mcp.log` | Odoo operations |
| `Logs/social_media_mcp.log` | Social media actions |
| `Logs/ralph_wiggum_loop.log` | Autonomous loop activity |
| `Logs/loop_stats.jsonl` | Loop statistics |
| `Accounting/Odoo/transactions.jsonl` | Financial transactions |

### HITL Requirements

Gold Tier maintains strict human-in-the-loop:

**Requires Approval:**
- All invoice creation
- All payments
- All social media posts
- All journal entries
- Any action that failed 3 retries

**Auto-Approved:**
- Reading data (list invoices, customers)
- Generating reports
- Content summarization
- Dashboard updates

---

## 📈 Performance Tuning

### Ralph Wiggum Loop Interval

```bash
# Aggressive (every 1 minute)
python scripts\ralph_wiggum_loop.py --continuous --interval 60

# Balanced (every 5 minutes) - RECOMMENDED
python scripts\ralph_wiggum_loop.py --continuous --interval 300

# Conservative (every 15 minutes)
python scripts\ralph_wiggum_loop.py --continuous --interval 900
```

### Batch Operations

For high-volume periods:

```bash
# Process only critical items
python scripts\ralph_wiggum_loop.py --run --priority-only

# Full system sweep
python scripts\ralph_wiggum_loop.py --run --full-scan
```

---

## 🚨 Troubleshooting

### Odoo Connection Issues

**Problem:** Cannot connect to Odoo
- **Solution:** Verify ODOO_URL and credentials in `.env`
- **Check:** `python mcp-servers\odoo_accounting_mcp.py --cli`

### Social Media API Errors

**Problem:** Posts not publishing
- **Solution:** Check API tokens are valid and not expired
- **Check:** `python mcp-servers\social_media_mcp.py --cli`

### Ralph Wiggum Loop Stuck

**Problem:** Loop not processing tasks
- **Solution:** Check `Logs/ralph_wiggum_loop.log` for errors
- **Check:** `python scripts\ralph_wiggum_loop.py --status`

### CEO Briefing Empty

**Problem:** Briefing shows no data
- **Solution:** Ensure logs exist and have recent entries
- **Check:** Run at least one loop cycle first

---

## 📝 Example Workflows

### Workflow 1: Invoice Processing

```
1. Email arrives with invoice PDF
   ↓
2. WhatsApp watcher saves to Inbox/
   ↓
3. Ralph Wiggum Loop creates Plan.md
   ↓
4. Odoo MCP creates invoice (pending approval)
   ↓
5. Human approves via approval_workflow.py
   ↓
6. Invoice validated in Odoo
   ↓
7. Plan moved to Done/
   ↓
8. CEO Briefing updated with revenue
```

### Workflow 2: Cross-Platform Social Post

```
1. Marketing team sends content via WhatsApp
   ↓
2. Ralph Wiggum Loop analyzes content
   ↓
3. Social Media MCP generates summaries
   ↓
4. Cross-post created for FB, IG, Twitter
   ↓
5. Human reviews in Pending_Approval/
   ↓
6. Approved → Scheduled
   ↓
7. Posts published at scheduled time
   ↓
8. Results logged for CEO Briefing
```

### Workflow 3: Autonomous Task Completion

```
1. Task arrives in Inbox/
   ↓
2. Ralph Wiggum Loop observes
   ↓
3. Creates Plan.md with 5 steps
   ↓
4. Executes step 1 ✅
   ↓
5. Executes step 2 ✅
   ↓
6. Step 3 fails → Retry (3x)
   ↓
7. Still fails → Escalate to human
   ↓
8. Human fixes issue
   ↓
9. Loop resumes, completes steps 3-5
   ↓
10. Task archived to Done/
```

---

## 🎓 Best Practices

### 1. Review Escalations Daily
```bash
python scripts\approval_workflow.py --list
```

### 2. Generate Weekly Briefings Every Friday
```bash
python scripts\ceo_briefing_generator.py --weekly
```

### 3. Monitor Loop Health
```bash
python scripts\ralph_wiggum_loop.py --status
```

### 4. Clean Up Old Plans Monthly
```bash
# Move completed plans to Done/
python scripts\claude_reasoning_loop.py --process
```

### 5. Backup Vault Weekly
```bash
# Copy AI_Employee_Vault to backup location
```

---

## 📞 Support & Resources

### Log Files

| Component | Log Location |
|-----------|--------------|
| Ralph Wiggum | `AI_Employee_Vault/Logs/ralph_wiggum_loop.log` |
| CEO Briefing | `AI_Employee_Vault/Logs/ceo_briefing.log` |
| Odoo MCP | `AI_Employee_Vault/Logs/odoo_mcp.log` |
| Social MCP | `AI_Employee_Vault/Logs/social_media_mcp.log` |
| MCP Gateway | `AI_Employee_Vault/Logs/mcp_gateway.log` |

### State Files

| Component | State Location |
|-----------|----------------|
| Ralph Wiggum | `AI_Employee_Vault/Plans/ralph_state.json` |
| Social Media | `AI_Employee_Vault/watchers/social_media_state.json` |
| Odoo | `AI_Employee_Vault/Accounting/Odoo/state.json` |

---

*AI Employee Gold Tier v0.3*  
*Complete: 2026-02-25*  
*"Me fail English? That's unpossible!" - Ralph Wiggum*
