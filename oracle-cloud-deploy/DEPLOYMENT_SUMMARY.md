# AI Employee Cloud Deployment - Quick Reference

## 🚀 One-Command Deployment

```bash
# Basic deployment (default thresholds)
sudo ./scripts/cloud-deploy.sh

# Full deployment with custom settings
sudo ./scripts/cloud-deploy.sh \
    --user oracle \
    --domain your-domain.com \
    --payment-threshold 500 \
    --email-threshold 100
```

## 📋 Post-Deployment Checklist

### 1. Configure Environment (REQUIRED)
```bash
cd /home/oracle/ai-employee
cp .env.example .env
nano .env  # Fill in API keys, database password, etc.
```

### 2. Setup HTTPS (Recommended)
```bash
sudo certbot --nginx -d your-domain.com
```

### 3. Configure Vault Sync
```bash
# On VM
cd /home/oracle/ai-employee
./scripts/vault-sync.sh --remote <git-url> setup
./scripts/vault-sync.sh sync

# On local machine
python scripts/local-sync.py --setup
python scripts/local-sync.py --sync
```

### 4. Setup Notifications
```bash
./scripts/notify-started.sh setup
```

### 5. Verify Deployment
```bash
./scripts/health-check.sh
```

## 🔧 Common Commands

### Service Management
```bash
# Status
systemctl status ai-employee-*

# Restart all
sudo systemctl restart ai-employee-orchestrator
sudo systemctl restart ai-employee-watcher
sudo systemctl restart ai-employee-vault-sync
sudo systemctl restart ai-employee-security-enforcer
sudo systemctl restart odoo

# Enable on boot
sudo systemctl enable ai-employee-*
```

### Monitoring
```bash
# Health check
./scripts/health-check.sh

# View logs
journalctl -u ai-employee-orchestrator -f
journalctl -u odoo -f

# Check status
sudo -u oracle ./services/orchestrator.py --status
```

### Vault Sync
```bash
# Manual sync
./scripts/vault-sync.sh sync

# Push only
./scripts/vault-sync.sh push

# Pull only
./scripts/vault-sync.sh pull

# Status
./scripts/vault-sync.sh status
```

### Security
```bash
# Run security scan
python3 platinum/security/security_enforcer.py --scan

# Auto-fix issues
python3 platinum/security/security_enforcer.py --fix

# Generate audit report
python3 platinum/security/security_enforcer.py --audit
```

## 📊 Architecture Overview

```
Cloud VM (Oracle/AWS)
├── 24/7 Services (systemd)
│   ├── Orchestrator      - Main coordination
│   ├── Watcher           - Task monitoring
│   ├── Vault Sync        - Git sync daemon
│   ├── Security Enforcer - Approval workflows
│   └── Odoo ERP          - Business operations
│
├── Directories
│   ├── /home/oracle/ai-employee/
│   │   ├── vault/            - Git-synced data
│   │   ├── config/           - Configuration
│   │   ├── platinum/security/- Security enforcer
│   │   └── logs/             - Service logs
│   │
│   ├── /opt/odoo/            - Odoo installation
│   ├── /var/backups/         - Automated backups
│   └── /var/log/             - System logs
│
└── Security
    ├── Payment approval > $100
    ├── Email approval > 50 recipients
    ├── Secret detection
    └── Audit logging

Local Machine
└── local-sync.py
    ├── Push to cloud
    ├── Pull from cloud
    └── Excludes secrets
```

## 🔐 Security Thresholds

| Action | Threshold | Approval Required |
|--------|-----------|-------------------|
| Payment | > $100 | Yes |
| Bulk Email | > 50 recipients | Yes |
| File with Secrets | Any | Quarantine |
| Permission Change | .env files | Auto-fix to 600 |

## 📁 Key Files

| File | Purpose |
|------|---------|
| `/home/oracle/ai-employee/.env` | Environment variables (secrets) |
| `/home/oracle/ai-employee/config/orchestrator.json` | Service config |
| `/home/oracle/ai-employee/platinum/security/security_config.json` | Security rules |
| `/var/backups/ai-employee/` | Automated backups |
| `/var/log/ai-employee/` | Service logs |

## 🐛 Troubleshooting

### Service Not Starting
```bash
# Check logs
journalctl -u <service-name> -n 50

# Check config
python3 -m py_compile /home/oracle/ai-employee/services/orchestrator.py

# Restart
sudo systemctl restart <service-name>
```

### Can't Access Odoo
```bash
# Check if running
systemctl status odoo

# Check port
netstat -tlnp | grep 8069

# Check Nginx
systemctl status nginx
nginx -t
```

### Sync Not Working
```bash
# Test SSH
ssh -i ~/.ssh/vault_sync_key oracle@<vm-ip>

# Check git
cd /home/oracle/ai-employee
git remote -v
git status
```

### Security Enforcer Blocking
```bash
# View audit log
cat /home/oracle/ai-employee/platinum/security/audit/audit_log.jsonl | jq

# Check quarantine
ls -la /home/oracle/ai-employee/platinum/security/quarantine/

# Temporarily disable (not recommended)
sudo systemctl stop ai-employee-security-enforcer
```

## 📈 Resource Monitoring

### Disk Usage
```bash
df -h
du -sh /home/oracle/ai-employee/*
```

### Memory Usage
```bash
free -h
htop
```

### Process Status
```bash
ps aux | grep -E "(odoo|orchestrator|watcher)"
```

### Log Size
```bash
du -sh /var/log/ai-employee/
du -sh /var/log/odoo/
```

## 💾 Backup & Restore

### Manual Backup
```bash
# Database
sudo -u postgres pg_dump -Fc odoo > odoo_backup.dump

# Vault
tar -czf vault_backup.tar.gz /home/oracle/ai-employee/vault/

# Config
tar -czf config_backup.tar.gz /home/oracle/ai-employee/config/
```

### Restore
```bash
# Database
sudo -u postgres pg_restore -d odoo odoo_backup.dump

# Vault
tar -xzf vault_backup.tar.gz -C /home/oracle/ai-employee/
```

## 🔔 Notification Setup

### Slack
1. Create incoming webhook in Slack
2. Run: `./scripts/notify-started.sh setup`
3. Enter webhook URL

### Microsoft Teams
1. Create webhook in Teams channel
2. Run: `./scripts/notify-started.sh setup`
3. Enter webhook URL

### Email
1. Configure SMTP in `.env`
2. Add recipients in `config/notifications.json`

## 📞 Support Commands

### Get Help
```bash
./scripts/cloud-deploy.sh --help
./scripts/vault-sync.sh --help
python scripts/local-sync.py --help
```

### Generate Report
```bash
# Full system report
./scripts/health-check.sh 2>&1 | tee health_report.txt

# Security audit
python3 platinum/security/security_enforcer.py --audit
```

### Reset Services
```bash
# Stop all
sudo systemctl stop ai-employee-*
sudo systemctl stop odoo

# Start all
sudo systemctl start postgresql
sudo systemctl start odoo
sudo systemctl start ai-employee-*

# Verify
./scripts/health-check.sh
```

## 🎯 Performance Tuning

### Odoo Workers
Edit `/opt/odoo/odoo.conf`:
```ini
workers = 4  # CPU cores * 2
max_cron_threads = 1
limit_time_cpu = 60
limit_time_real = 120
```

### PostgreSQL
Edit `/etc/postgresql/*/main/postgresql.conf`:
```ini
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 10MB
```

### Nginx Rate Limiting
Already configured in `/etc/nginx/sites-available/ai-employee`:
- API: 10 requests/second
- Login: 5 requests/minute

## 📚 Documentation Links

- [Full README](README_CLOUD_DEPLOY.md)
- [CEO Briefing System](../ceo-briefing-system/README_ENHANCED.md)
- [Security Enforcer](../platinum/security/README.md)
- [Odoo MCP](../odoo-mcp-server/README.md)

---

*Quick Reference for AI Employee Cloud Deployment*
*For detailed documentation, see README_CLOUD_DEPLOY.md*
