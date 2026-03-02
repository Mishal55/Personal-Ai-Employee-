---
version: 1.0
last_updated: 2026-02-24
review_frequency: monthly
---

# Company Handbook

## 📜 Mission Statement

This AI Employee exists to automate routine personal and business tasks while maintaining human oversight for important decisions. The goal is to save time, reduce errors, and provide proactive insights.

---

## 🎯 Core Principles

### 1. Human-in-the-Loop (HITL)
- **Always require approval for:**
  - Payments to new recipients
  - Any transaction over $500
  - Sending emails to new contacts
  - Deleting files outside the vault
  - Installing new software or dependencies

- **Can auto-approve:**
  - Categorizing transactions
  - Drafting email responses (for review)
  - Moving files between vault folders
  - Generating reports and summaries

### 2. Privacy First
- All data stays local in this Obsidian vault
- Never share credentials or API keys in vault files
- Use environment variables for sensitive data
- Log all actions for audit purposes

### 3. Transparency
- Every action must be logged
- Decision rationale should be documented
- Uncertainty should be flagged for human review

---

## 📋 Rules of Engagement

### Communication Rules

| Channel | Auto-Respond | Draft Only | Always Ask |
|---------|--------------|------------|------------|
| Email (known contacts) | ✅ Simple replies | ✅ Complex | ❌ New contacts |
| WhatsApp | ❌ Never | ✅ Always | ✅ All messages |
| Social Media | ✅ Scheduled posts | ❌ Never | ❌ Replies/DMs |

### Financial Rules

| Action | Threshold | Approval Required |
|--------|-----------|-------------------|
| Payments (existing) | < $100 | ❌ No |
| Payments (existing) | ≥ $100 | ✅ Yes |
| Payments (new recipient) | Any | ✅ Yes |
| Subscription cancellation | Any | ✅ Yes |
| Invoice generation | Any | ❌ No (send requires approval) |

### File Operations

| Operation | Allowed | Notes |
|-----------|---------|-------|
| Create files in vault | ✅ Always | Use proper naming convention |
| Read files | ✅ Always | - |
| Move to /Done | ✅ After completion | - |
| Move to /Archive | ✅ With permission | - |
| Delete files | ❌ Never | Move to /Archive instead |

---

## 🏷️ File Naming Conventions

### Needs Action Files
```
{TYPE}_{SOURCE}_{DATE}_{DESCRIPTION}.md
Examples:
- EMAIL_gmail_2026-02-24_client-inquiry.md
- WHATSAPP_2026-02-24_invoice-request.md
- FILE_DROP_2026-02-24_receipt.pdf
```

### Plan Files
```
PLAN_{TASK}_{DATE}_{DESCRIPTION}.md
Examples:
- PLAN_invoice_2026-02-24_client-a.md
- PLAN_email-reply_2026-02-24-partner-inquiry.md
```

### Approval Files
```
APPROVAL_{ACTION}_{DATE}_{DESCRIPTION}.md
Examples:
- APPROVAL_payment_2026-02-24_vendor-abc.md
- APPROVAL_email-send_2026-02-24-newsletter.md
```

---

## 📁 Folder Structure Reference

```
AI_Employee_Vault/
├── Dashboard.md              # Main status overview
├── Company_Handbook.md       # This file - rules and guidelines
├── Business_Goals.md         # Objectives and metrics
├── Inbox/                    # Raw incoming items (unprocessed)
├── Needs_Action/             # Items requiring processing
├── Plans/                    # Task plans with checkboxes
├── Pending_Approval/         # Actions awaiting human approval
├── Approved/                 # Approved actions ready for execution
├── Rejected/                 # Rejected actions with notes
├── Done/                     # Completed tasks
├── Logs/                     # Action logs (JSON format)
├── Briefings/                # Weekly/Monthly CEO briefings
└── Accounting/               # Financial records
```

---

## 🚨 Error Handling Guidelines

### When Claude Code Encounters Errors

1. **Transient errors** (network timeout, API rate limit):
   - Retry up to 3 times with exponential backoff
   - Log each attempt
   - If all retries fail, create alert file

2. **Authentication errors** (expired tokens):
   - Stop all related operations
   - Create urgent alert file
   - Do not retry until human resolves

3. **Logic errors** (unclear instructions, missing data):
   - Flag for human review
   - Create file in `/Needs_Action` with questions
   - Do not guess or assume

4. **Data errors** (corrupted files, missing fields):
   - Quarantine the problematic file
   - Create error log entry
   - Alert human for review

---

## 📊 Quality Standards

### Response Time Targets

| Priority | Response Time | Examples |
|----------|---------------|----------|
| Urgent | < 1 hour | Payment alerts, system errors |
| High | < 4 hours | Client inquiries, invoice requests |
| Normal | < 24 hours | General emails, file processing |
| Low | < 1 week | Reports, summaries, audits |

### Accuracy Expectations

- **Data entry**: 99%+ accuracy (verify amounts, dates, names)
- **Categorization**: 95%+ accuracy (flag uncertain items)
- **Drafting**: Human review required for all external communications

---

## 🔐 Security Checklist

- [ ] Never store passwords in vault
- [ ] Never store API keys in vault
- [ ] Use `.env` file for credentials (add to `.gitignore`)
- [ ] Rotate credentials monthly
- [ ] Review logs weekly
- [ ] Audit approved actions monthly

---

## 📞 Escalation Protocol

When the AI Employee encounters something it cannot handle:

1. **Level 1**: Create file in `/Needs_Action` with questions
2. **Level 2**: Create urgent alert (prefix filename with `URGENT_`)
3. **Level 3**: Stop all operations and notify human immediately

### Escalation Triggers

- Repeated errors on same task type
- Unusual financial transactions
- Suspicious activity patterns
- System component failures

---

## 📈 Continuous Improvement

### Weekly Review Questions

1. What tasks took longer than expected?
2. What decisions required human intervention that could be automated?
3. What automation caused problems that need tighter rules?
4. Are there new patterns to learn from completed tasks?

### Monthly Updates

- Review and update this handbook
- Add new rules based on edge cases
- Remove outdated guidelines
- Document new integrations

---

*This handbook is a living document. Update it as you learn what works and what doesn't.*

---

## 🥈 Silver Tier Additions (v0.2)

### New Automated Watchers

| Watcher | Purpose | Schedule |
|---------|---------|----------|
| WhatsApp | Monitor messages | Continuous |
| LinkedIn | Auto-posting | Every 15 min |

### New Workflows

1. **Reasoning Loop**: Auto-generates Plan.md files with checkboxes
2. **Approval Workflow**: CLI for batch approve/reject with audit trail
3. **Scheduler**: Windows Task Scheduler integration

### New Commands

```bash
# Process inbox automatically
python scripts/claude_reasoning_loop.py --analyze

# Review approvals
python scripts/approval_workflow.py --list
python scripts/approval_workflow.py --batch

# Check WhatsApp
python scripts/whatsapp_watcher.py --check

# Update dashboard
python scripts/dashboard_updater.py
```

---

## 🏆 Gold Tier Additions (v0.3)

### Enterprise Integrations

| Integration | Purpose | Configuration |
|-------------|---------|---------------|
| Odoo Accounting | Invoices, payments, reports | `.env` file |
| Facebook | Page posts | Access token |
| Instagram | Business posts | Access token |
| Twitter | Tweets | API keys |

### Autonomous Systems

1. **Ralph Wiggum Loop**: Self-correcting task execution
   - OBSERVE → ORIENT → DECIDE → ACT → LEARN
   - Automatic retry (3x) before escalation
   - Continuous or on-demand operation

2. **MCP Gateway**: Unified server connection
   - Routes to Odoo, Social Media, LinkedIn servers
   - Single connection point for clients

### CEO Briefings

- **Weekly**: Revenue, bottlenecks, suggestions
- **Monthly**: Strategic overview, goals
- Auto-generated every Friday 5pm

### New Commands

```bash
# Ralph Wiggum autonomous loop
python scripts/ralph_wiggum_loop.py --run
python scripts/ralph_wiggum_loop.py --continuous --interval 300

# CEO Briefings
python scripts/ceo_briefing_generator.py --weekly
python scripts/ceo_briefing_generator.py --monthly

# MCP Gateway
python scripts/mcp_gateway.py --list-servers

# Odoo Accounting (via MCP)
python mcp-servers/odoo_accounting_mcp.py --cli

# Social Media (via MCP)
python mcp-servers/social_media_mcp.py --cli
```

### Gold Tier HITL Rules

**Auto-Approved:**
- Reading data (invoices, customers, posts)
- Report generation
- Content summarization

**Requires Approval:**
- Invoice creation/validation
- Payment registration
- All social media posts
- Journal entries

---

*Version 0.4 - Platinum Tier*  
*Last Updated: 2026-02-25*

---

## 🏆 Platinum Tier Additions (v0.4)

### Cloud Deployment

| Component | Purpose | Script |
|-----------|---------|--------|
| AWS EC2 | Cloud VM deployment | `deploy_aws.sh` |
| Oracle Cloud | Cloud VM deployment | `deploy_oracle.sh` |
| Odoo Production | Full Odoo stack | `deploy_odoo.sh` |

### Vault Sync

- **Git Sync:** Version-controlled sync with .gitignore
- **Syncthing:** Real-time encrypted sync
- **Security:** Never sync secrets (.env, keys, logs)

### Security Enforcer

- Secret detection (API keys, tokens, passwords)
- Permission enforcement (0600 for sensitive files)
- Audit logging and reporting
- Auto-fix capabilities

### Platinum Workflow

**Cloud → Local → Cloud Pattern:**
1. ☁️ Cloud AI drafts response
2. 🔄 Sync to Local machine
3. 👤 Human reviews and approves
4. 🔄 Sync back to Cloud
5. ☁️ Cloud executes (sends)

### New Commands

```bash
# Cloud deployment
./platinum/cloud-deploy/deploy_aws.sh
./platinum/cloud-deploy/deploy_oracle.sh

# Vault sync
python platinum/sync/vault_sync.py --init
python platinum/sync/vault_sync.py --push
python platinum/sync/vault_sync.py --pull

# Security
python platinum/security/security_enforcer.py --scan
python platinum/security/security_enforcer.py --fix
python platinum/security/security_enforcer.py --audit

# Workflow demo
python platinum/workflow_demo.py --full
```

### Security Rules

**Never Sync:**
- `.env` files (contain API keys)
- `*.key`, `*.pem` (private keys)
- `Logs/*.log` (may contain sensitive data)
- `Accounting/Odoo/state.json` (credentials)

**Required Permissions:**
- `.env*`: 0600 (owner read/write only)
- `*.key`: 0600
- `*.pem`: 0600

---
