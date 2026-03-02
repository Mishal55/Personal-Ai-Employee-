# AI Employee Cloud Deployment

Complete deployment solution for Oracle/AWS Cloud VM with 24/7 monitoring, Git-based vault sync, Security Enforcer, and Odoo Community ERP.

## 🚀 Features

### 1. 24/7 Orchestrator + Watchers
- **Continuous Operation**: Systemd services run 24/7 with auto-restart
- **Health Monitoring**: 5-minute health checks with auto-remediation
- **Resource Management**: CPU, memory, and I/O prioritization
- **Log Rotation**: Automated log management with 30-day retention

### 2. Git-Based Vault Sync
- **Bidirectional Sync**: Local ↔ Cloud synchronization
- **Secret Exclusion**: Automatic exclusion of .env, tokens, credentials
- **Conflict Resolution**: Smart merge with local preference
- **Automatic Sync**: Every 5 minutes via daemon

### 3. Security Enforcer (Platinum Tier)
- **Approval Thresholds**:
  - Payments > $100 require approval
  - Bulk emails > 50 require approval
- **Secret Detection**: Scans for exposed API keys, tokens, passwords
- **File Permissions**: Enforces secure permissions (600 for secrets)
- **Audit Logging**: Complete audit trail in JSONL format
- **Quarantine**: Unsafe files moved to quarantine

### 4. Odoo Community Production Deployment
- **Odoo 16.0**: Latest stable Community edition
- **HTTPS**: Let's Encrypt SSL certificates
- **PostgreSQL**: Optimized database configuration
- **Nginx Reverse Proxy**: Rate limiting, security headers
- **Automated Backups**: Daily backups with 30-day retention

### 5. Monitoring & Alerting
- **Health Checks**: Every 5 minutes
- **Multi-Channel Alerts**: Slack, Teams, Email
- **Resource Monitoring**: Disk, memory, CPU alerts
- **Service Status**: Real-time systemd service monitoring

## 📁 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Oracle/AWS Cloud VM                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  systemd services (24/7 with health monitoring)         │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐  │    │
│  │  │ Orchestrator │ │   Watcher    │ │  Vault Sync    │  │    │
│  │  │   Service    │ │   Service    │ │    Service     │  │    │
│  │  └──────────────┘ └──────────────┘ └────────────────┘  │    │
│  │  ┌──────────────┐ ┌──────────────┐                     │    │
│  │  │   Security   │ │     Odoo     │                     │    │
│  │  │   Enforcer   │ │   ERP (16)   │                     │    │
│  │  └──────────────┘ └──────────────┘                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │  /home/oracle/ai-employee/                                │  │
│  │  ├── scripts/          # Deployment & sync scripts       │  │
│  │  ├── services/         # Python services (orchestrator)  │  │
│  │  ├── config/           # Configuration (non-secret)      │  │
│  │  ├── vault/            # Git-synced vault                │  │
│  │  │   ├── Needs_Action/ # Tasks pending action            │  │
│  │  │   ├── Done/         # Completed tasks                 │  │
│  │  │   ├── Pending_Approval/                               │  │
│  │  │   └── Briefings/    # CEO briefings                   │  │
│  │  ├── platinum/security/  # Security Enforcer             │  │
│  │  │   ├── quarantine/   # Quarantined files               │  │
│  │  │   └── audit/        # Audit logs                      │  │
│  │  └── logs/             # Service logs                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↕ rsync over SSH (excludes secrets)│
┌─────────────────────────────────────────────────────────────────┐
│                    Local Machine                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  local-sync.py                                           │    │
│  │  - Bidirectional sync                                   │    │
│  │  - Excludes: .env, tokens, credentials, secrets         │    │
│  │  - Conflict resolution                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

### Cloud VM
- **Oracle Cloud**: VM.Standard.E2.1.Micro (minimum) or VM.Standard.E4.Flex
- **AWS**: t3.medium or larger
- **OS**: Oracle Linux 8/9, Ubuntu 22.04+, or Amazon Linux 2
- **Storage**: Minimum 50GB
- **Network**: Public IP, SSH access (port 22)

### Local Machine
- Python 3.8+
- rsync (for local-sync.py)
- Git
- SSH client

## 🚀 Quick Start

### 1. Deploy to Cloud VM

```bash
# SSH into your VM
ssh -i <your-key> oracle@<vm-ip>

# Clone deployment scripts
git clone <your-repo>/oracle-cloud-deploy.git
cd oracle-cloud-deploy

# Run deployment (default thresholds: payment>$100, email>50)
sudo ./scripts/cloud-deploy.sh

# Or with custom thresholds
sudo ./scripts/cloud-deploy.sh \
    --payment-threshold 500 \
    --email-threshold 100 \
    --domain your-domain.com
```

### 2. Configure Environment

```bash
# On the VM
cd /home/oracle/ai-employee
cp .env.example .env
nano .env  # Fill in your values
```

### 3. Setup Vault Sync

```bash
# On the VM - configure git remote
cd /home/oracle/ai-employee
./scripts/vault-sync.sh --remote <your-git-repo-url> setup

# Initial sync
./scripts/vault-sync.sh sync
```

### 4. Configure Local Sync

```bash
# On your local machine
cd oracle-cloud-deploy
python scripts/local-sync.py --setup

# Sync to cloud
python scripts/local-sync.py --sync
```

### 5. Setup Notifications

```bash
# On the VM
cd /home/oracle/ai-employee
./scripts/notify-started.sh setup
```

## 📖 Directory Structure

```
oracle-cloud-deploy/
├── scripts/
│   ├── cloud-deploy.sh         # Main deployment script
│   ├── vault-sync.sh           # Git vault sync
│   ├── vault-sync-daemon.sh    # Continuous sync daemon
│   ├── local-sync.py           # Local sync client
│   ├── notify-started.sh       # Notification script
│   ├── health-check.sh         # Health check script
│   └── backup.sh               # Backup script
├── services/
│   ├── orchestrator.py         # Main orchestrator
│   └── security_enforcer.py    # Security Enforcer
├── systemd/
│   ├── ai-employee-*.service   # Service definitions
│   └── odoo.service
├── config/
│   ├── orchestrator.json.example
│   ├── local-sync.json.example
│   ├── sync-config.json.example
│   └── notifications.json.example
├── .gitignore                  # Excludes secrets
└── README_CLOUD_DEPLOY.md      # This file
```

## 🔧 Configuration

### Security Thresholds

Set during deployment or edit `/home/oracle/ai-employee/platinum/security/security_config.json`:

```json
{
    "approval_thresholds": {
        "payment_amount": 100,
        "bulk_email_count": 50,
        "require_dual_approval": true
    }
}
```

### Orchestrator Config

Edit `/home/oracle/ai-employee/config/orchestrator.json`:

```json
{
    "watchers": {
        "enabled": true,
        "restart_on_failure": true,
        "health_check_interval": 30
    },
    "vault_sync": {
        "enabled": true,
        "sync_interval": 300,
        "auto_push": true,
        "auto_pull": true
    },
    "tasks": {
        "ceo_briefing": {
            "enabled": true,
            "schedule": "0 7 * * 1"
        },
        "invoice_processing": {
            "enabled": true,
            "schedule": "*/30 * * * *"
        }
    }
}
```

### Local Sync Config

Edit `config/local-sync.json`:

```json
{
    "cloud_host": "192.168.1.100",
    "cloud_user": "oracle",
    "cloud_path": "/home/oracle/ai-employee",
    "local_path": "/path/to/local/vault",
    "ssh_key": "~/.ssh/vault_sync_key",
    "sync_mode": "bidirectional"
}
```

## 🛡️ Security Features

### Secret Detection

The Security Enforcer scans for:
- API keys (OpenAI, Anthropic, AWS)
- Access tokens
- Private keys
- Passwords
- Credentials files

### File Permissions

Enforced permissions:
- `.env` files: 600 (owner read/write only)
- `*.key`, `*.pem`: 600
- Config files: 640

### Git Exclusion

The `.gitignore` excludes:
- `.env*` files
- `*.token`, `*.key`, `*.secret`
- `*credentials*`
- `secrets/`, `tokens/` directories

### Approval Workflow

```
Payment Request > $100
    ↓
Security Enforcer blocks execution
    ↓
Notification sent to approvers
    ↓
Approver reviews in portal
    ↓
Approved → Payment processed
Rejected → Request denied
```

## 🔍 Monitoring

### Health Check

```bash
# Run health check
/home/oracle/ai-employee/scripts/health-check.sh

# Or view systemd timer
systemctl status ai-employee-health-check.timer
```

### Service Status

```bash
# All services
systemctl status ai-employee-*

# Individual service
systemctl status ai-employee-orchestrator
```

### Logs

```bash
# Real-time logs
journalctl -u ai-employee-orchestrator -f

# Last 100 lines
journalctl -u ai-employee-watcher -n 100

# Security audit log
cat /home/oracle/ai-employee/platinum/security/audit/audit_log.jsonl
```

## 💾 Backups

### Automated Backups

- **Schedule**: Daily at 2 AM
- **Retention**: 30 days
- **Location**: `/var/backups/ai-employee/`

### Manual Backup

```bash
# Backup database
sudo -u postgres pg_dump -Fc odoo > odoo_backup.dump

# Backup vault
tar -czf vault_backup.tar.gz /home/oracle/ai-employee/vault/
```

### Restore

```bash
# Restore database
sudo -u postgres pg_restore -d odoo odoo_backup.dump

# Restore vault
tar -xzf vault_backup.tar.gz -C /home/oracle/ai-employee/
```

## 🔔 Notifications

### Configure Channels

```bash
# Interactive setup
./scripts/notify-started.sh setup

# Or edit config/notifications.json
```

### Notification Types

- **Deployment**: Success/failure alerts
- **Health Check**: Service unhealthy alerts
- **Security**: Secret detection, approval requests
- **Approval**: Payment/email threshold exceeded

## 📊 Service Management

### Start/Stop/Restart

```bash
sudo systemctl start ai-employee-orchestrator
sudo systemctl stop ai-employee-orchestrator
sudo systemctl restart ai-employee-orchestrator
```

### Enable on Boot

```bash
sudo systemctl enable ai-employee-orchestrator
sudo systemctl enable ai-employee-watcher
sudo systemctl enable ai-employee-vault-sync
sudo systemctl enable ai-employee-security-enforcer
sudo systemctl enable odoo
```

### View Status

```bash
# JSON status
sudo -u oracle /home/oracle/ai-employee/services/orchestrator.py --status
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u ai-employee-orchestrator -n 50

# Check Python syntax
python3 -m py_compile /home/oracle/ai-employee/services/orchestrator.py

# Check permissions
ls -la /home/oracle/ai-employee/
```

### Sync Fails

```bash
# Test SSH
ssh -i ~/.ssh/vault_sync_key oracle@<vm-ip>

# Test git remote
cd /home/oracle/ai-employee
git remote -v
git fetch origin
```

### Security Enforcer Issues

```bash
# Run security scan
python3 /home/oracle/ai-employee/platinum/security/security_enforcer.py --scan

# View audit log
cat /home/oracle/ai-employee/platinum/security/audit/audit_log.jsonl | jq
```

### Odoo Issues

```bash
# Check Odoo logs
journalctl -u odoo -f

# Test database connection
psql -U odoo -d odoo -h localhost
```

## 📈 Resource Requirements

### Minimum (Small Deployment)
- 2 vCPUs
- 4GB RAM
- 50GB storage
- Suitable for: < 10 users

### Recommended (Medium Deployment)
- 4 vCPUs
- 8GB RAM
- 100GB storage
- Suitable for: 10-50 users

### Production (Large Deployment)
- 8+ vCPUs
- 16GB+ RAM
- 200GB+ storage
- Suitable for: 50+ users

## 🔐 Security Best Practices

1. **Use SSH Keys**: Never use password authentication
2. **Firewall**: Only open required ports (22, 80, 443)
3. **Regular Updates**: `sudo dnf update` or `sudo apt update && apt upgrade`
4. **Monitor Logs**: Review `/var/log/ai-employee/` regularly
5. **Backup Encryption**: Encrypt backups before storing offsite
6. **Rotate Secrets**: Change API keys and passwords regularly

## 📚 Additional Resources

- [CEO Briefing System](../ceo-briefing-system/README_ENHANCED.md)
- [Odoo MCP Server](../odoo-mcp-server/README.md)
- [Security Enforcer](../platinum/security/README.md)

## 📞 Support

For issues or questions:
1. Check logs: `journalctl -u ai-employee-*`
2. Run health check: `./scripts/health-check.sh`
3. Review security audit: `security_enforcer.py --audit`

---

*AI Employee Cloud Deployment - Production-ready autonomous employee infrastructure*
