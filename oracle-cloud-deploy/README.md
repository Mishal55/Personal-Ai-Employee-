# Oracle Cloud VM Deployment

Deploy AI Employee services to Oracle Cloud Infrastructure (OCI) with 24/7 watchers, orchestrator, and Git-based vault sync.

## Features

- 🔄 **24/7 Watchers** - Systemd services that run continuously
- 🎯 **Orchestrator** - Central coordination of all services
- 🔐 **Git Vault Sync** - Secure synchronization excluding secrets
- 📦 **Automated Deployment** - One-command deployment script
- 🔔 **Health Monitoring** - Auto-restart on failure
- 📝 **Log Rotation** - Managed log retention

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Oracle Cloud VM                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  systemd services (24/7)                                 │    │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌───────────┐  │    │
│  │  │ ai-employee-    │ │ ai-employee-    │ │ ai-employee│  │    │
│  │  │ watcher.service │ │ orchestrator    │ │ vault-sync │  │    │
│  │  └─────────────────┘ └─────────────────┘ └───────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │                    AI Employee Vault                       │  │
│  │  /home/oracle/ai-employee/                                 │  │
│  │  ├── scripts/          # Deployment & utility scripts     │  │
│  │  ├── services/         # Python services                  │  │
│  │  ├── config/           # Configuration (non-secret)       │  │
│  │  ├── vault/            # Git-synced vault                 │  │
│  │  │   ├── Needs_Action/ # Tasks pending action             │  │
│  │  │   ├── Done/         # Completed tasks                  │  │
│  │  │   └── Pending_Approval/                                │  │
│  │  └── logs/             # Service logs                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↕ SSH/rsync (excludes secrets)
┌─────────────────────────────────────────────────────────────────┐
│                    Local Machine                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  local-sync.py                                           │    │
│  │  - Push local changes to cloud                          │    │
│  │  - Pull cloud changes to local                          │    │
│  │  - Excludes: .env, tokens, credentials, secrets         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Oracle Cloud VM
- Oracle Linux 8/9 or Ubuntu 22.04+
- Root or sudo access
- Minimum 2 vCPUs, 4GB RAM
- Public IP or SSH access

### Local Machine
- Python 3.8+
- SSH client
- rsync (for local-sync.py)
- Git

## Quick Start

### 1. Deploy to Oracle Cloud VM

```bash
# SSH into your Oracle Cloud VM
ssh -i <your-key> oracle@<vm-ip>

# Clone or copy deployment scripts
git clone <your-repo>/oracle-cloud-deploy.git
cd oracle-cloud-deploy

# Run deployment script
sudo ./scripts/deploy.sh
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

## Directory Structure

```
oracle-cloud-deploy/
├── scripts/
│   ├── deploy.sh              # Main deployment script
│   ├── vault-sync.sh          # Git vault sync script
│   ├── vault-sync-daemon.sh   # Continuous sync daemon
│   └── local-sync.py          # Local sync client
├── services/
│   └── orchestrator.py        # Main orchestrator service
├── systemd/
│   ├── ai-employee-watcher.service
│   ├── ai-employee-orchestrator.service
│   └── ai-employee-vault-sync.service
├── config/
│   ├── sync-config.json.example
│   ├── orchestrator.json.example
│   └── local-sync.json.example
├── .gitignore                 # Excludes secrets
└── README.md
```

## Service Management

### Check Status

```bash
# All services
systemctl status ai-employee-*

# Individual service
systemctl status ai-employee-watcher.service
```

### Start/Stop/Restart

```bash
sudo systemctl start ai-employee-watcher.service
sudo systemctl stop ai-employee-watcher.service
sudo systemctl restart ai-employee-watcher.service
```

### View Logs

```bash
# Real-time logs
journalctl -u ai-employee-watcher -f

# Last 100 lines
journalctl -u ai-employee-watcher -n 100

# Since boot
journalctl -u ai-employee-watcher -b
```

### Enable on Boot

```bash
sudo systemctl enable ai-employee-watcher.service
sudo systemctl enable ai-employee-orchestrator.service
sudo systemctl enable ai-employee-vault-sync.service
```

## Vault Sync

### Git-Based Sync (Excludes Secrets)

The `.gitignore` file excludes:
- `.env` files
- `*.token`, `*.key`, `*.secret`
- `*credentials*`, `*api_key*`
- `tokens/`, `secrets/` directories
- `node_modules/`, `__pycache__/`
- `logs/`, `*.log`

### Sync Commands

```bash
# Initialize git repo
./scripts/vault-sync.sh init

# Setup remote
./scripts/vault-sync.sh --remote <url> setup

# Push changes
./scripts/vault-sync.sh push

# Pull changes
./scripts/vault-sync.sh pull

# Full sync
./scripts/vault-sync.sh sync

# Check status
./scripts/vault-sync.sh status

# Verify secrets excluded
./scripts/vault-sync.sh verify
```

### Automatic Sync (Cron)

```bash
# Add cron job (every 15 minutes)
./scripts/vault-sync.sh cron-add

# Remove cron job
./scripts/vault-sync.sh cron-remove
```

## Local Sync Client

### Setup

```bash
# Interactive setup
python scripts/local-sync.py --setup

# Or edit config directly
cp config/local-sync.json.example config/local-sync.json
nano config/local-sync.json
```

### Commands

```bash
# Show status
python scripts/local-sync.py --status

# Check connection
python scripts/local-sync.py --check

# Push to cloud
python scripts/local-sync.py --push

# Pull from cloud
python scripts/local-sync.py --pull

# Bidirectional sync
python scripts/local-sync.py --sync
```

## Configuration

### Environment Variables (.env)

```bash
# Oracle Cloud
OCI_REGION=us-ashburn-1
OCI_COMPARTMENT_ID=ocid1.compartment.oc1...

# Database
DATABASE_URL=postgresql://user:pass@localhost/db
DATABASE_PASSWORD=

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Odoo
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=

# Vault Sync
VAULT_SYNC_REMOTE=oracle@<vm-ip>:/vault.git
VAULT_SYNC_BRANCH=vault-sync
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
  "tasks": {
    "ceo_briefing": {
      "enabled": true,
      "schedule": "0 7 * * 1"
    }
  }
}
```

## Security

### SSH Key Setup

```bash
# Generate key for vault sync
ssh-keygen -t ed25519 -f ~/.ssh/vault_sync_key -N ""

# Copy public key to VM
ssh-copy-id -i ~/.ssh/vault_sync_key.pub oracle@<vm-ip>
```

### Firewall Rules

```bash
# Oracle Linux
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-port=8069/tcp
sudo firewall-cmd --reload

# Ubuntu
sudo ufw allow ssh
sudo ufw allow 8069/tcp
```

### Security Hardening

The systemd services include:
- `NoNewPrivileges=true`
- `ProtectSystem=strict`
- `ProtectHome=read-only`
- `PrivateTmp=true`

## Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u ai-employee-watcher -n 50

# Check config
python3 -m py_compile /home/oracle/ai-employee/services/orchestrator.py

# Check permissions
ls -la /home/oracle/ai-employee/
```

### Sync Fails

```bash
# Test SSH connection
ssh -i ~/.ssh/vault_sync_key oracle@<vm-ip>

# Test git remote
cd /home/oracle/ai-employee
git remote -v
git fetch origin
```

### Check Resource Usage

```bash
# Memory
htop

# Disk
df -h

# Logs size
du -sh /var/log/ai-employee/
```

## Monitoring

### Health Check Endpoint

```bash
# Run health check
sudo -u oracle /home/oracle/ai-employee/services/orchestrator.py --check
```

### Service Status API

```bash
# Get JSON status
sudo -u oracle /home/oracle/ai-employee/services/orchestrator.py --status
```

## Backup

### Manual Backup

```bash
# Backup vault data
tar -czf vault-backup-$(date +%Y%m%d).tar.gz \
    /home/oracle/ai-employee/vault/
```

### Automated Backup

The `data_backup` task runs daily at 2 AM via the orchestrator.

## License

MIT
