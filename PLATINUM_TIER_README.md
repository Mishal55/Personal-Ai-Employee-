# AI Employee Platinum Tier - Enterprise Deployment Guide

> **Version:** 0.4 (Platinum Tier)  
> **Release Date:** 2026-02-25  
> **Previous Version:** 0.3 (Gold Tier)

---

## 🏆 What's New in Platinum Tier

Platinum Tier adds **cloud deployment**, **secure synchronization**, **enterprise security**, and **distributed execution**:

| Feature | Gold | Platinum |
|---------|------|----------|
| All Gold Features | ✅ | ✅ |
| **Cloud VM Deployment** | ❌ | ✅ |
| **Vault Sync (Git/Syncthing)** | ❌ | ✅ |
| **Security Enforcement** | ❌ | ✅ |
| **Odoo Production Deploy** | ❌ | ✅ |
| **Cloud→Local→Cloud Workflow** | ❌ | ✅ |
| **Automated Backups** | ❌ | ✅ |
| **Health Monitoring** | ❌ | ✅ |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLOUD VM (AWS/Oracle)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ AI Employee │  │   Odoo 16   │  │  Nginx + PostgreSQL     │  │
│  │   Scripts   │  │  Community  │  │  + Monitoring           │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────────────┘  │
│         │                │                                        │
│         └────────┬───────┘                                        │
│                  │                                                │
│         ┌────────▼────────┐                                       │
│         │  Git/Syncthing  │ ◄────── Sync ──────► Local Machine   │
│         │    Sync Layer   │                                       │
│         └─────────────────┘                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      LOCAL MACHINE (Your PC)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Obsidian  │  │  Approval   │  │  Security Enforcer      │  │
│  │    Vault    │  │  Workflow   │  │  (No secrets sync)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Complete Directory Structure

```
D:\Personal Ai Employee\
├── platinum/                          # Platinum Tier files
│   ├── cloud-deploy/
│   │   ├── deploy_aws.sh             # AWS deployment script
│   │   └── deploy_oracle.sh          # Oracle Cloud script
│   ├── sync/
│   │   ├── vault_sync.py             # Sync manager (Git/Syncthing)
│   │   └── syncthing_config.xml      # Syncthing template
│   ├── security/
│   │   ├── security_enforcer.py      # Security scanner
│   │   └── audit_*.md                # Audit reports
│   ├── odoo-deploy/
│   │   └── deploy_odoo.sh            # Odoo production deploy
│   ├── workflow_demo.py              # Workflow demonstration
│   └── workflow_log.jsonl            # Workflow execution log
├── scripts/                           # All AI Employee scripts
├── mcp-servers/                       # MCP servers
└── AI_Employee_Vault/                 # Synced vault
```

---

## 🚀 Quick Start

### Step 1: Deploy Cloud VM

**Option A: AWS Free Tier (t2.micro)**

```bash
# Launch EC2 instance (Ubuntu 22.04)
# Then run deployment script:
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
scp -i your-key.pem platinum/cloud-deploy/deploy_aws.sh ubuntu@YOUR_EC2_IP:~
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
./deploy_aws.sh
```

**Option B: Oracle Cloud Free Tier (A1.Flex)**

```bash
# Launch VM.Standard.A1.Flex instance (Ubuntu 22.04)
scp -i your-key.pem platinum/cloud-deploy/deploy_oracle.sh ubuntu@YOUR_IP:~
ssh -i your-key.pem ubuntu@YOUR_IP
./deploy_oracle.sh
```

### Step 2: Setup Vault Sync

**On Cloud VM (initialize bare Git repo):**

```bash
cd /home/aiemployee
python platinum/sync/vault_sync.py --init --bare
```

**On Local Machine (initialize working repo):**

```bash
cd "D:\Personal Ai Employee\AI_Employee_Vault"
python platinum/sync/vault_sync.py --init
python platinum/sync/vault_sync.py --remote "ssh://aiemployee@YOUR_CLOUD_IP:/home/aiemployee/ai-employee-vault.git"
python platinum/sync/vault_sync.py --push
```

### Step 3: Run Security Scan

```bash
# Scan for security violations
python platinum/security/security_enforcer.py --scan

# Generate audit report
python platinum/security/security_enforcer.py --audit
```

### Step 4: Deploy Odoo (on Cloud)

```bash
# SSH to cloud VM
scp platinum/odoo-deploy/deploy_odoo.sh ubuntu@YOUR_CLOUD_IP:~
./deploy_odoo.sh

# Save the admin password displayed!
```

---

## 📋 Platinum Commands Reference

### Cloud Deployment

```bash
# AWS deployment
./platinum/cloud-deploy/deploy_aws.sh

# Oracle Cloud deployment
./platinum/cloud-deploy/deploy_oracle.sh

# Monitor cloud VM
ssh aiemployee@CLOUD_IP
sudo /usr/local/bin/ai-employee-monitor.sh
```

### Vault Sync

```bash
# Initialize Git sync (local)
python platinum/sync/vault_sync.py --init

# Initialize bare repo (cloud)
python platinum/sync/vault_sync.py --init --bare

# Push changes to cloud
python platinum/sync/vault_sync.py --push

# Pull changes from cloud
python platinum/sync/vault_sync.py --pull

# Check sync status
python platinum/sync/vault_sync.py --status

# Generate Syncthing config
python platinum/sync/vault_sync.py --method syncthing --init
```

### Security

```bash
# Scan for violations
python platinum/security/security_enforcer.py --scan

# Auto-fix issues
python platinum/security/security_enforcer.py --fix

# Generate audit report
python platinum/security/security_enforcer.py --audit
```

### Workflow Demo

```bash
# Run complete workflow
python platinum/workflow_demo.py --full

# Run individual steps
python platinum/workflow_demo.py --step 1  # Cloud drafts
python platinum/workflow_demo.py --step 2  # Sync to local
python platinum/workflow_demo.py --step 3  # Local approves
python platinum/workflow_demo.py --step 4  # Sync to cloud
python platinum/workflow_demo.py --step 5  # Cloud executes
```

---

## 🔒 Security Features

### Never-Sync List

The following files are **blocked from sync** by `.gitignore`:

```
.env                    # Contains API keys
.env.*                  # All environment files
*.key                   # Private keys
*.pem                   # Certificates
Logs/*.log              # May contain sensitive data
Accounting/Odoo/state.json  # Contains credentials
```

### Secret Detection

The Security Enforcer scans for:

| Pattern | Severity |
|---------|----------|
| API Keys | Critical |
| Access Tokens | Critical |
| Passwords | Critical |
| Private Keys | Critical |
| JWT Tokens | Critical |
| AWS Credentials | Critical |

### Permission Enforcement

| File Type | Required Permission |
|-----------|---------------------|
| `.env*` | 0600 (owner rw) |
| `*.key` | 0600 (owner rw) |
| `*.pem` | 0600 (owner rw) |

---

## ☁️ Cloud VM Configuration

### AWS Free Tier Specifications

| Setting | Value |
|---------|-------|
| Instance | t2.micro (1 vCPU, 1GB RAM) |
| Storage | 8GB GP2 |
| OS | Ubuntu 22.04 LTS |
| Security Group | SSH (22), HTTP (80), HTTPS (443), Odoo (8069) |

### Oracle Cloud Free Tier Specifications

| Setting | Value |
|---------|-------|
| Instance | VM.Standard.A1.Flex (4 vCPU, 24GB RAM) |
| Storage | 50GB Block Volume |
| OS | Ubuntu 22.04 LTS |
| Firewall | Allow 22, 80, 443, 8069 |

---

## 🔄 Sync Methods Comparison

### Git Sync (Recommended)

**Pros:**
- Version history
- Conflict resolution
- Selective sync via .gitignore
- Works over SSH

**Cons:**
- Manual push/pull (or cron)
- Not real-time

**Best for:** Most deployments

### Syncthing

**Pros:**
- Real-time sync
- Automatic conflict detection
- Encrypted transfer
- No central server needed

**Cons:**
- Both machines must be online
- More complex setup

**Best for:** Always-on machines

---

## 📊 Workflow Patterns

### Pattern 1: Cloud Drafts → Local Approves → Cloud Executes

```
1. ☁️  Cloud AI receives email
2. ☁️  Cloud drafts reply → Pending_Approval/
3. 🔄 Git sync to Local
4. 👤 Human reviews on Local
5. 👤 Human approves → Approved/
6. 🔄 Git sync to Cloud
7. ☁️  Cloud sends email → Done/
```

### Pattern 2: Local Creates → Cloud Publishes

```
1. 👤 Human creates social post on Local
2. 🔄 Sync to Cloud
3. ☁️  Cloud schedules post
4. ☁️  Cloud publishes at scheduled time
```

### Pattern 3: Cloud Processes → Local Reviews

```
1. ☁️  Cloud processes invoices
2. ☁️  Cloud creates accounting entries
3. 🔄 Sync to Local
4. 👤 Human reviews reports
```

---

## 💾 Backup Strategy

### Automated Backups (Cloud VM)

| Backup Type | Schedule | Retention |
|-------------|----------|-----------|
| Database (pg_dump) | Daily 2 AM | 7 days |
| Filestore (tar) | Daily 2 AM | 7 days |
| Config | Daily 2 AM | 7 days |

### Manual Backup Commands

```bash
# Full Odoo backup
sudo /usr/local/bin/odoo-backup.sh

# Download backups locally
scp -i key.pem ubuntu@CLOUD_IP:/backups/odoo/*.gz ./backups/
```

### Restore from Backup

```bash
# Restore database
gunzip < db_20260225_020000.sql.gz | sudo -u postgres psql odoo

# Restore filestore
sudo tar -xzf filestore_20260225_020000.tar.gz -C /var/lib/odoo/
```

---

## 📈 Monitoring

### Health Check Script

```bash
# Run health check
/usr/local/bin/ai-employee-monitor.sh

# Check health status
cat /var/log/odoo/health_status.json
```

### Health Status Format

```json
{
    "timestamp": "2026-02-25T10:00:00+00:00",
    "services": {
        "odoo": "healthy",
        "postgresql": "healthy",
        "nginx": "healthy"
    },
    "disk": {
        "status": "healthy",
        "usage_percent": 45
    }
}
```

### Service Status Commands

```bash
# Check all services
systemctl status odoo ai-employee-ralph ai-employee-scheduler

# View logs
tail -f /var/log/odoo/odoo-server.log
journalctl -u odoo -f
```

---

## 🚨 Troubleshooting

### Sync Issues

**Problem:** Git push fails
- **Solution:** Check SSH keys, verify remote URL
- **Check:** `git remote -v`

**Problem:** Conflicts during sync
- **Solution:** Pull first, resolve conflicts, then push
- **Check:** `git status`

### Security Enforcer Issues

**Problem:** False positive on secrets
- **Solution:** Add to skip patterns in security_enforcer.py
- **Check:** Review flagged content context

### Cloud VM Issues

**Problem:** Can't connect via SSH
- **Solution:** Check security group, verify key permissions
- **Check:** `chmod 400 your-key.pem`

**Problem:** Services not starting
- **Solution:** Check logs, verify dependencies
- **Check:** `systemctl status <service>`

---

## 📝 Example Deployment

### Complete Setup (Step by Step)

**1. Launch AWS EC2:**
```bash
# AWS Console → EC2 → Launch Instance
# - Ubuntu 22.04
# - t2.micro
# - Create key pair
# - Security group: 22, 80, 443, 8069
```

**2. Deploy to Cloud:**
```bash
scp -i ai-employee.pem platinum/cloud-deploy/deploy_aws.sh ubuntu@EC2_IP:~
ssh -i ai-employee.pem ubuntu@EC2_IP
./deploy_aws.sh
```

**3. Setup Local Sync:**
```bash
cd "D:\Personal Ai Employee\AI_Employee_Vault"
git init
git remote add cloud ssh://aiemployee@EC2_IP:/home/aiemployee/ai-employee-vault.git
echo ".env" >> .gitignore
git add .
git commit -m "Initial vault"
git push -u cloud main
```

**4. Run Security Scan:**
```bash
python platinum/security/security_enforcer.py --scan
python platinum/security/security_enforcer.py --audit
```

**5. Test Workflow:**
```bash
python platinum/workflow_demo.py --full
```

---

## 🔐 Security Checklist

- [ ] SSH keys secured (chmod 400)
- [ ] Firewall configured (UFW/firewalld)
- [ ] Fail2Ban installed and running
- [ ] .env files excluded from sync
- [ ] Database passwords changed from defaults
- [ ] SSL certificates installed (Let's Encrypt)
- [ ] Regular security audits scheduled
- [ ] Backup restoration tested

---

## 📞 Support Resources

### Log Locations

| Component | Cloud Path | Local Path |
|-----------|-----------|------------|
| Odoo | `/var/log/odoo/` | - |
| AI Employee | `~/AI_Employee_Vault/Logs/` | Same |
| Sync | - | `platinum/sync/sync_log.jsonl` |
| Security | - | `platinum/security/audit_log.jsonl` |
| Workflow | - | `platinum/workflow_log.jsonl` |

### Configuration Files

| File | Location |
|------|----------|
| Odoo Config | `/etc/odoo.conf` |
| AI Employee Env | `~/.env` |
| Nginx Config | `/etc/nginx/sites-available/odoo` |
| Systemd Services | `/etc/systemd/system/` |

---

*AI Employee Platinum Tier v0.4*  
*Complete: 2026-02-25*  
*"Enterprise-grade autonomous AI employee"*
