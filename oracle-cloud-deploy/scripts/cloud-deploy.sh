#!/bin/bash
# ============================================
# AI Employee Cloud Deployment Script
# Complete deployment for Oracle/AWS Cloud VM
# Features:
#   - 24/7 Orchestrator + Watchers with health monitoring
#   - Git-based vault sync (excludes secrets)
#   - Security Enforcer with approval thresholds
#   - Odoo Community production deployment
#   - HTTPS with Let's Encrypt
#   - Automated backups
#   - Monitoring & alerting
# ============================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_USER="${DEPLOY_USER:-oracle}"
DEPLOY_DIR="${DEPLOY_DIR:-/home/${DEPLOY_USER}/ai-employee}"
ODOO_DIR="${ODOO_DIR:-/opt/odoo}"
SYSTEMD_DIR="/etc/systemd/system"
LOG_DIR="/var/log/ai-employee"
ODOO_LOG_DIR="/var/log/odoo"
BACKUP_DIR="/var/backups/ai-employee"
SSL_DIR="/etc/letsencrypt"

# Security thresholds
PAYMENT_APPROVAL_THRESHOLD="${PAYMENT_APPROVAL_THRESHOLD:-100}"
EMAIL_BULK_THRESHOLD="${EMAIL_BULK_THRESHOLD:-50}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] $1"
}

log_info() { log "${BLUE}[INFO]${NC} $1"; }
log_success() { log "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { log "${YELLOW}[WARN]${NC} $1"; }
log_error() { log "${RED}[ERROR]${NC} $1"; }
log_step() { log "${PURPLE}[STEP]${NC} $1"; }
log_security() { log "${CYAN}[SECURITY]${NC} $1"; }

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root"
        log_info "Usage: sudo ./cloud-deploy.sh"
        exit 1
    fi
}

# Detect OS version
detect_os() {
    log_info "Detecting operating system..."

    if [ -f /etc/os-release ]; then
        source /etc/os-release
        OS_VERSION="$PRETTY_NAME"
        OS_ID="$ID"
        log_info "Detected: $OS_VERSION"
    else
        log_error "Could not detect OS version"
        exit 1
    fi
}

# Update system packages
update_system() {
    log_step "Updating system packages..."

    if command -v apt &> /dev/null; then
        apt update && apt upgrade -y
    elif command -v dnf &> /dev/null; then
        dnf update -y
    elif command -v yum &> /dev/null; then
        yum update -y
    fi

    log_success "System packages updated"
}

# Install required packages
install_packages() {
    log_step "Installing required packages..."

    local common_packages=(
        git curl wget jq htop iotop net-tools unzip zip
        python3 python3-pip python3-venv python3-dev
        nodejs npm build-essential
        postgresql postgresql-contrib libpq-dev
        nginx certbot python3-certbot-nginx
        supervisor redis-tools
    )

    if command -v apt &> /dev/null; then
        apt install -y "${common_packages[@]}"
        # Additional Ubuntu packages
        apt install -y software-properties-common
    elif command -v dnf &> /dev/null; then
        dnf install -y "${common_packages[@]}"
        dnf install -y epel-release
    elif command -v yum &> /dev/null; then
        yum install -y "${common_packages[@]}"
        yum install -y epel-release
    fi

    log_success "Required packages installed"
}

# Create deployment user
create_user() {
    log_step "Setting up deployment user: $DEPLOY_USER"

    if ! id "$DEPLOY_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$DEPLOY_USER"
        log_info "Created user: $DEPLOY_USER"
    else
        log_info "User already exists: $DEPLOY_USER"
    fi

    # Add to sudo group
    if command -v usermod &> /dev/null; then
        usermod -aG sudo "$DEPLOY_USER" 2>/dev/null || usermod -aG wheel "$DEPLOY_USER" 2>/dev/null || true
    fi

    # Configure sudo without password for specific commands
    cat > /etc/sudoers.d/$DEPLOY_USER << EOF
$DEPLOY_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart ai-employee-*, /usr/bin/systemctl restart odoo
EOF
    chmod 440 /etc/sudoers.d/$DEPLOY_USER

    log_success "Deployment user configured"
}

# Create directory structure
create_directories() {
    log_step "Creating directory structure..."

    # Main deployment directories
    mkdir -p "$DEPLOY_DIR"/{scripts,services,config,logs,data,vault,mcp-servers}
    mkdir -p "$DEPLOY_DIR"/vault/{Needs_Action,Done,Pending_Approval,Briefings}
    mkdir -p "$DEPLOY_DIR"/platinum/security/{quarantine,audit}

    # Odoo directories
    mkdir -p "$ODOO_DIR"/{addons,data,logs}
    mkdir -p "$ODOO_LOG_DIR"

    # System directories
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKUP_DIR"/{database,files,odoo}
    mkdir -p "$SSL_DIR"

    # Set ownership
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$ODOO_DIR"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$BACKUP_DIR"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$ODOO_LOG_DIR"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$LOG_DIR"

    # Set permissions
    chmod 755 "$DEPLOY_DIR"
    chmod 700 "$DEPLOY_DIR"/config
    chmod 755 "$ODOO_DIR"
    chmod 750 "$BACKUP_DIR"

    log_success "Directory structure created"
}

# Setup Python virtual environment
setup_python_env() {
    log_step "Setting up Python virtual environment..."

    cd "$DEPLOY_DIR"

    # Create virtual environment
    python3 -m venv venv

    # Activate and upgrade pip
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel

    # Install requirements
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt"
    fi

    # Install common packages
    pip install requests python-dotenv schedule psycopg2-binary

    log_success "Python environment setup complete"
}

# Setup Node.js environment
setup_node_env() {
    log_step "Setting up Node.js environment..."

    cd "$DEPLOY_DIR"

    # Install global packages
    npm install -g nodemon pm2

    # Install MCP server dependencies
    if [ -d "$DEPLOY_DIR/mcp-servers" ]; then
        for dir in "$DEPLOY_DIR/mcp-servers"/*/; do
            if [ -f "${dir}package.json" ]; then
                log_info "Installing dependencies for $(basename $dir)"
                cd "$dir" && npm install
            fi
        done
    fi

    log_success "Node.js environment setup complete"
}

# Deploy application scripts
deploy_scripts() {
    log_step "Deploying application scripts..."

    # Copy scripts from source
    cp -r "$SCRIPT_DIR/scripts/"* "$DEPLOY_DIR/scripts/" 2>/dev/null || true
    cp -r "$SCRIPT_DIR/services/"* "$DEPLOY_DIR/services/" 2>/dev/null || true

    # Make scripts executable
    chmod +x "$DEPLOY_DIR/scripts/"*.sh 2>/dev/null || true
    chmod +x "$DEPLOY_DIR/services/"*.py 2>/dev/null || true

    # Set ownership
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/scripts"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/services"

    log_success "Scripts deployed"
}

# Deploy Security Enforcer
deploy_security_enforcer() {
    log_step "Deploying Security Enforcer..."

    # Copy security enforcer
    if [ -f "$SCRIPT_DIR/services/security_enforcer.py" ]; then
        cp "$SCRIPT_DIR/services/security_enforcer.py" "$DEPLOY_DIR/platinum/security/"
        chmod +x "$DEPLOY_DIR/platinum/security/security_enforcer.py"
    fi

    # Create security configuration
    cat > "$DEPLOY_DIR/platinum/security/security_config.json" << EOF
{
    "approval_thresholds": {
        "payment_amount": $PAYMENT_APPROVAL_THRESHOLD,
        "bulk_email_count": $EMAIL_BULK_THRESHOLD,
        "require_dual_approval": true,
        "auto_reject_after_hours": false
    },
    "secret_patterns": [
        "API_KEY",
        "API_SECRET",
        "ACCESS_TOKEN",
        "PRIVATE_KEY",
        "PASSWORD",
        "AWS_ACCESS_KEY",
        "AWS_SECRET"
    ],
    "protected_files": [
        ".env",
        "*.key",
        "*.pem",
        "*credentials*",
        "config/*.json"
    ],
    "audit_log_path": "$DEPLOY_DIR/platinum/security/audit/audit_log.jsonl",
    "quarantine_path": "$DEPLOY_DIR/platinum/security/quarantine"
}
EOF

    chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/platinum/security/security_config.json"
    chmod 600 "$DEPLOY_DIR/platinum/security/security_config.json"

    log_security "Security Enforcer deployed with thresholds:"
    log_security "  - Payment approval: >\$${PAYMENT_APPROVAL_THRESHOLD}"
    log_security "  - Bulk email approval: >${EMAIL_BULK_THRESHOLD} emails"

    log_success "Security Enforcer deployed"
}

# Setup PostgreSQL
setup_postgresql() {
    log_step "Setting up PostgreSQL..."

    # Start PostgreSQL
    systemctl enable postgresql
    systemctl start postgresql

    # Create Odoo database user
    sudo -u postgres psql -c "CREATE USER odoo WITH CREATEDB PASSWORD 'odoo_secure_password_123';" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER odoo WITH SUPERUSER;" 2>/dev/null || true

    # Create database
    sudo -u postgres psql -c "CREATE DATABASE odoo OWNER odoo ENCODING 'UTF-8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8';" 2>/dev/null || true

    log_success "PostgreSQL setup complete"
}

# Deploy Odoo Community
deploy_odoo() {
    log_step "Deploying Odoo Community..."

    cd "$ODOO_DIR"

    # Clone Odoo Community (version 16.0)
    if [ ! -d "odoo" ]; then
        git clone --depth 1 --branch 16.0 https://github.com/odoo/odoo.git
    fi

    # Create Odoo configuration
    cat > "$ODOO_DIR/odoo.conf" << EOF
[options]
admin_passwd = admin_secure_password_123
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo_secure_password_123
db_name = odoo
data_dir = $ODOO_DIR/data
addons_path = $ODOO_DIR/odoo/addons,$ODOO_DIR/addons
logfile = $ODOO_LOG_DIR/odoo.log
log_level = info
http_port = 8069
workers = 4
max_cron_threads = 1
limit_time_cpu = 60
limit_time_real = 120
xmlrpc_interface = 127.0.0.1
EOF

    # Create requirements file and install
    cd "$ODOO_DIR/odoo"
    pip3 install -r requirements.txt

    # Set ownership
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$ODOO_DIR"

    log_success "Odoo Community deployed"
}

# Setup Nginx reverse proxy
setup_nginx() {
    log_step "Setting up Nginx reverse proxy..."

    # Create Nginx configuration
    cat > /etc/nginx/sites-available/ai-employee << EOF
# AI Employee & Odoo Reverse Proxy

# Rate limiting
limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=login_limit:10m rate=5r/m;

# Odoo upstream
upstream odoo_backend {
    server 127.0.0.1:8069;
    keepalive 32;
}

# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name _;

    # Let's Encrypt validation
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name _;

    # SSL configuration
    ssl_certificate $SSL_DIR/live/\$server_name/fullchain.pem;
    ssl_certificate_key $SSL_DIR/live/\$server_name/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Odoo proxy
    location / {
        limit_req zone=api_limit burst=20 nodelay;
        limit_req zone=login_limit burst=5 nodelay;

        proxy_pass http://odoo_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;

        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/ai-employee /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    # Test and reload Nginx
    nginx -t && systemctl reload nginx

    log_success "Nginx reverse proxy configured"
}

# Setup HTTPS with Let's Encrypt
setup_https() {
    log_step "Setting up HTTPS with Let's Encrypt..."

    local domain="${DOMAIN_NAME:-}"

    if [ -z "$domain" ]; then
        log_warn "No domain name provided. Skipping HTTPS setup."
        log_info "Run certbot manually: certbot --nginx -d your-domain.com"
        return 0
    fi

    # Create webroot for Let's Encrypt
    mkdir -p /var/www/certbot

    # Obtain certificate
    certbot certonly --webroot -w /var/www/certbot -d "$domain" --non-interactive --agree-tos --email admin@"$domain"

    # Setup auto-renewal
    systemctl enable certbot.timer
    systemctl start certbot.timer

    log_success "HTTPS configured for $domain"
}

# Deploy systemd services
deploy_systemd_services() {
    log_step "Deploying systemd services..."

    # Copy service files
    cp "$SCRIPT_DIR/systemd/"*.service "$SYSTEMD_DIR/" 2>/dev/null || true

    # Create orchestrator service
    cat > "$SYSTEMD_DIR/ai-employee-orchestrator.service" << EOF
[Unit]
Description=AI Employee Orchestrator Service
Documentation=https://github.com/ai-employee/oracle-cloud-deploy
After=network.target network-online.target postgresql.service odoo.service
Wants=network-online.target

[Service]
Type=simple
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$DEPLOY_DIR

Environment="PATH=/usr/local/bin:/usr/bin:/bin:$DEPLOY_DIR/venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONDONTWRITEBYTECODE=1"
EnvironmentFile=-$DEPLOY_DIR/.env

ExecStart=$DEPLOY_DIR/venv/bin/python3 $DEPLOY_DIR/services/orchestrator.py --daemon
ExecReload=/bin/kill -s HUP \$MAINPID

Restart=always
RestartSec=10
StartLimitInterval=0

Resource limits
LimitNOFILE=65535
Nice=-5

Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=$DEPLOY_DIR/logs
ReadWritePaths=$DEPLOY_DIR/data
ReadWritePaths=$DEPLOY_DIR/vault
ReadWritePaths=$LOG_DIR

StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-employee-orchestrator

[Install]
WantedBy=multi-user.target
EOF

    # Create watcher service
    cat > "$SYSTEMD_DIR/ai-employee-watcher.service" << EOF
[Unit]
Description=AI Employee Watcher Service
Documentation=https://github.com/ai-employee/oracle-cloud-deploy
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$DEPLOY_DIR

Environment="PATH=/usr/local/bin:/usr/bin:/bin:$DEPLOY_DIR/venv/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=-$DEPLOY_DIR/.env

ExecStart=$DEPLOY_DIR/venv/bin/python3 -m ai_employee.watchers.main
ExecReload=/bin/kill -s HUP \$MAINPID

Restart=always
RestartSec=10
StartLimitInterval=0

LimitNOFILE=65535
Nice=-5

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=$DEPLOY_DIR/logs
ReadWritePaths=$DEPLOY_DIR/data

StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-employee-watcher

[Install]
WantedBy=multi-user.target
EOF

    # Create vault sync service
    cat > "$SYSTEMD_DIR/ai-employee-vault-sync.service" << EOF
[Unit]
Description=AI Employee Vault Sync Service
Documentation=https://github.com/ai-employee/oracle-cloud-deploy
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$DEPLOY_DIR

Environment="PATH=/usr/local/bin:/usr/bin:/bin:$DEPLOY_DIR/venv/bin"
Environment="GIT_SSH_COMMAND=ssh -i $DEPLOY_DIR/.ssh/vault_sync_key"
EnvironmentFile=-$DEPLOY_DIR/.env

ExecStart=$DEPLOY_DIR/scripts/vault-sync-daemon.sh
ExecReload=/bin/kill -s HUP \$MAINPID

Restart=always
RestartSec=30

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=$DEPLOY_DIR/vault

StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-employee-vault-sync

[Install]
WantedBy=multi-user.target
EOF

    # Create Odoo service
    cat > "$SYSTEMD_DIR/odoo.service" << EOF
[Unit]
Description=Odoo ERP Service
Documentation=https://www.odoo.com
After=network.target network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$ODOO_DIR

Environment="PATH=/usr/local/bin:/usr/bin:/bin:$DEPLOY_DIR/venv/bin"
EnvironmentFile=-$DEPLOY_DIR/.env

ExecStart=$DEPLOY_DIR/venv/bin/python3 $ODOO_DIR/odoo/odoo-bin -c $ODOO_DIR/odoo.conf
ExecReload=/bin/kill -s HUP \$MAINPID

Restart=always
RestartSec=10

LimitNOFILE=65535

ReadWritePaths=$ODOO_DIR/data
ReadWritePaths=$ODOO_LOG_DIR

StandardOutput=journal
StandardError=journal
SyslogIdentifier=odoo

[Install]
WantedBy=multi-user.target
EOF

    # Create security enforcer service
    cat > "$SYSTEMD_DIR/ai-employee-security-enforcer.service" << EOF
[Unit]
Description=AI Employee Security Enforcer Service
Documentation=https://github.com/ai-employee/oracle-cloud-deploy
After=network.target

[Service]
Type=simple
User=$DEPLOY_USER
Group=$DEPLOY_USER
WorkingDirectory=$DEPLOY_DIR

Environment="PATH=/usr/local/bin:/usr/bin:/bin:$DEPLOY_DIR/venv/bin"
EnvironmentFile=-$DEPLOY_DIR/.env

ExecStart=$DEPLOY_DIR/venv/bin/python3 $DEPLOY_DIR/platinum/security/security_enforcer.py --daemon
ExecReload=/bin/kill -s HUP \$MAINPID

Restart=always
RestartSec=10

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=$DEPLOY_DIR/platinum/security

StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-employee-security

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload

    # Enable services
    systemctl enable ai-employee-orchestrator.service
    systemctl enable ai-employee-watcher.service
    systemctl enable ai-employee-vault-sync.service
    systemctl enable ai-employee-security-enforcer.service
    systemctl enable odoo.service

    log_success "Systemd services deployed"
}

# Setup automated backups
setup_backups() {
    log_step "Setting up automated backups..."

    # Create backup script
    cat > "$DEPLOY_DIR/scripts/backup.sh" << 'BACKUP_SCRIPT'
#!/bin/bash
# Automated backup script for AI Employee & Odoo

set -e

BACKUP_DIR="/var/backups/ai-employee"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directories
mkdir -p "$BACKUP_DIR"/{database,files,odoo}

echo "[$(date)] Starting backup..."

# Backup PostgreSQL databases
echo "Backing up databases..."
sudo -u postgres pg_dump -Fc odoo > "$BACKUP_DIR/database/odoo_$DATE.dump"
sudo -u postgres pg_dumpall > "$BACKUP_DIR/database/all_databases_$DATE.sql"

# Backup Odoo filestore
echo "Backing up Odoo filestore..."
tar -czf "$BACKUP_DIR/odoo/filestore_$DATE.tar.gz" /home/oracle/ai-employee/vault/ 2>/dev/null || true

# Backup configuration
echo "Backing up configuration..."
tar -czf "$BACKUP_DIR/files/config_$DATE.tar.gz" /home/oracle/ai-employee/config/ 2>/dev/null || true

# Remove old backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete

echo "[$(date)] Backup complete"
BACKUP_SCRIPT

    chmod +x "$DEPLOY_DIR/scripts/backup.sh"

    # Create backup systemd timer
    cat > "$SYSTEMD_DIR/ai-employee-backup.service" << EOF
[Unit]
Description=AI Employee Daily Backup
After=postgresql.service

[Service]
Type=oneshot
User=$DEPLOY_USER
ExecStart=$DEPLOY_DIR/scripts/backup.sh
EOF

    cat > "$SYSTEMD_DIR/ai-employee-backup.timer" << EOF
[Unit]
Description=Run AI Employee backup daily
Requires=ai-employee-backup.service

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Enable backup timer
    systemctl daemon-reload
    systemctl enable ai-employee-backup.timer
    systemctl start ai-employee-backup.timer

    log_success "Automated backups configured (daily at 2 AM)"
}

# Setup monitoring
setup_monitoring() {
    log_step "Setting up monitoring..."

    # Create health check script
    cat > "$DEPLOY_DIR/scripts/health-check.sh" << 'HEALTH_SCRIPT'
#!/bin/bash
# Health check script for AI Employee services

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local service=$1
    if systemctl is-active --quiet "$service"; then
        echo -e "  ${GREEN}✓${NC} $service"
        return 0
    else
        echo -e "  ${RED}✗${NC} $service"
        return 1
    fi
}

echo "================================"
echo "  AI Employee Health Check"
echo "================================"
echo ""

failed=0

echo "Services:"
check_service "ai-employee-orchestrator" || ((failed++))
check_service "ai-employee-watcher" || ((failed++))
check_service "ai-employee-vault-sync" || ((failed++))
check_service "ai-employee-security-enforcer" || ((failed++))
check_service "odoo" || ((failed++))
check_service "postgresql" || ((failed++))
check_service "nginx" || ((failed++))

echo ""
echo "Resources:"

# Check disk space
disk_usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$disk_usage" -lt 80 ]; then
    echo -e "  ${GREEN}✓${NC} Disk usage: ${disk_usage}%"
else
    echo -e "  ${YELLOW}⚠${NC} Disk usage: ${disk_usage}%"
    ((failed++))
fi

# Check memory
mem_usage=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
if [ "$mem_usage" -lt 80 ]; then
    echo -e "  ${GREEN}✓${NC} Memory usage: ${mem_usage}%"
else
    echo -e "  ${YELLOW}⚠${NC} Memory usage: ${mem_usage}%"
    ((failed++))
fi

echo ""
if [ $failed -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$failed check(s) failed${NC}"
    exit 1
fi
HEALTH_SCRIPT

    chmod +x "$DEPLOY_DIR/scripts/health-check.sh"

    # Create monitoring systemd timer
    cat > "$SYSTEMD_DIR/ai-employee-health-check.service" << EOF
[Unit]
Description=AI Employee Health Check

[Service]
Type=oneshot
User=$DEPLOY_USER
ExecStart=$DEPLOY_DIR/scripts/health-check.sh
EOF

    cat > "$SYSTEMD_DIR/ai-employee-health-check.timer" << EOF
[Unit]
Description=Run AI Employee health check every 5 minutes
Requires=ai-employee-health-check.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Enable health check timer
    systemctl daemon-reload
    systemctl enable ai-employee-health-check.timer
    systemctl start ai-employee-health-check.timer

    log_success "Monitoring configured (health checks every 5 minutes)"
}

# Create environment file
create_env_file() {
    log_step "Creating environment file..."

    cat > "$DEPLOY_DIR/.env.example" << 'EOF'
# AI Employee Environment Configuration
# Copy this file to .env and fill in your values
# DO NOT commit .env to git!

# Oracle/AWS Cloud Configuration
CLOUD_PROVIDER=oracle
OCI_REGION=us-ashburn-1
OCI_COMPARTMENT_ID=

# Database Configuration
DATABASE_URL=postgresql://odoo:odoo_secure_password_123@localhost/odoo
DATABASE_PASSWORD=odoo_secure_password_123

# API Keys (Add your own)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Odoo Configuration
ODOO_URL=http://127.0.0.1:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=admin_secure_password_123

# Vault Sync Configuration
VAULT_SYNC_REMOTE=
VAULT_SYNC_BRANCH=vault-sync

# Security Thresholds
PAYMENT_APPROVAL_THRESHOLD=100
EMAIL_BULK_THRESHOLD=50

# Logging
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=30

# Feature Flags
ENABLE_CEO_BRIEFING=true
ENABLE_INVOICE_PROCESSING=true
ENABLE_VAULT_SYNC=true
ENABLE_SECURITY_ENFORCER=true
EOF

    chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/.env.example"
    chmod 640 "$DEPLOY_DIR/.env.example"

    log_success "Environment file template created"
    log_warn "Copy .env.example to .env and fill in your values!"
}

# Setup SSH keys for vault sync
setup_ssh_keys() {
    log_step "Setting up SSH keys for vault sync..."

    local ssh_dir="/home/${DEPLOY_USER}/.ssh"

    mkdir -p "$ssh_dir"

    # Generate key if not exists
    if [ ! -f "$ssh_dir/vault_sync_key" ]; then
        sudo -u "$DEPLOY_USER" ssh-keygen -t ed25519 -f "$ssh_dir/vault_sync_key" -N "" -C "vault-sync@ai-employee"
        log_info "Generated new SSH key for vault sync"
    else
        log_info "SSH key already exists"
    fi

    # Set permissions
    chmod 700 "$ssh_dir"
    chmod 600 "$ssh_dir/vault_sync_key"
    chmod 644 "$ssh_dir/vault_sync_key.pub"

    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$ssh_dir"

    log_success "SSH keys configured"
    log_info "Public key: $ssh_dir/vault_sync_key.pub"
    log_info "Add this key to your Git repository for vault sync"
}

# Setup log rotation
setup_log_rotation() {
    log_step "Setting up log rotation..."

    cat > /etc/logrotate.d/ai-employee << EOF
$LOG_DIR/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $DEPLOY_USER $DEPLOY_USER
    postrotate
        systemctl reload ai-employee-watcher.service 2>/dev/null || true
        systemctl reload ai-employee-orchestrator.service 2>/dev/null || true
    endscript
}

$ODOO_LOG_DIR/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $DEPLOY_USER $DEPLOY_USER
    postrotate
        systemctl reload odoo.service 2>/dev/null || true
    endscript
}
EOF

    log_success "Log rotation configured"
}

# Setup firewall
setup_firewall() {
    log_step "Configuring firewall..."

    if command -v firewall-cmd &> /dev/null; then
        # Oracle Linux / firewalld
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --permanent --add-port=8069/tcp
        firewall-cmd --reload
    elif command -v ufw &> /dev/null; then
        # Ubuntu / UFW
        ufw allow ssh
        ufw allow http
        ufw allow https
        ufw allow 8069/tcp
        ufw --force enable
    fi

    log_success "Firewall configured"
}

# Start services
start_services() {
    log_step "Starting services..."

    # Start PostgreSQL
    systemctl start postgresql

    # Start Odoo
    systemctl start odoo
    sleep 5

    # Start AI Employee services
    systemctl start ai-employee-orchestrator.service
    systemctl start ai-employee-watcher.service
    systemctl start ai-employee-vault-sync.service
    systemctl start ai-employee-security-enforcer.service

    # Start Nginx
    systemctl start nginx

    # Wait for services to stabilize
    sleep 10

    # Check status
    log_info "Service status:"
    systemctl status ai-employee-orchestrator.service --no-pager -l 2>/dev/null || true
    systemctl status ai-employee-watcher.service --no-pager -l 2>/dev/null || true
    systemctl status odoo.service --no-pager -l 2>/dev/null || true
    systemctl status nginx.service --no-pager -l 2>/dev/null || true

    log_success "Services started"
}

# Run security scan
run_security_scan() {
    log_step "Running initial security scan..."

    if [ -f "$DEPLOY_DIR/platinum/security/security_enforcer.py" ]; then
        sudo -u "$DEPLOY_USER" "$DEPLOY_DIR/venv/bin/python3" "$DEPLOY_DIR/platinum/security/security_enforcer.py" --scan || true
    fi

    log_success "Security scan complete"
}

# Print deployment summary
print_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}    Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Deployment Directory:${NC} $DEPLOY_DIR"
    echo -e "${BLUE}Odoo Directory:${NC} $ODOO_DIR"
    echo -e "${BLUE}Log Directory:${NC} $LOG_DIR"
    echo -e "${BLUE}Backup Directory:${NC} $BACKUP_DIR"
    echo -e "${BLUE}User:${NC} $DEPLOY_USER"
    echo ""
    echo -e "${CYAN}Security Configuration:${NC}"
    echo "  - Payment approval threshold: >\$${PAYMENT_APPROVAL_THRESHOLD}"
    echo "  - Bulk email approval threshold: >${EMAIL_BULK_THRESHOLD} emails"
    echo "  - Security Enforcer: Active"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. SSH into the VM as $DEPLOY_USER"
    echo "2. Copy and configure .env file:"
    echo "   cp $DEPLOY_DIR/.env.example $DEPLOY_DIR/.env"
    echo "   nano $DEPLOY_DIR/.env"
    echo ""
    echo "3. Setup HTTPS (if you have a domain):"
    echo "   sudo certbot --nginx -d your-domain.com"
    echo ""
    echo "4. Configure vault sync:"
    echo "   cd $DEPLOY_DIR"
    echo "   ./scripts/vault-sync.sh --remote <your-git-remote> setup"
    echo ""
    echo "5. Check service status:"
    echo "   systemctl status ai-employee-*"
    echo ""
    echo "6. Run health check:"
    echo "   $DEPLOY_DIR/scripts/health-check.sh"
    echo ""
    echo "7. View logs:"
    echo "   journalctl -u ai-employee-orchestrator -f"
    echo ""
    echo -e "${GREEN}========================================${NC}"
}

# Main deployment function
main() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  AI Employee Cloud Deployment${NC}"
    echo -e "${BLUE}  Oracle/AWS VM with Odoo ERP${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    check_root
    detect_os

    log_info "Starting deployment..."

    update_system
    install_packages
    create_user
    create_directories
    setup_postgresql
    deploy_odoo
    setup_python_env
    setup_node_env
    deploy_scripts
    deploy_security_enforcer
    setup_nginx
    setup_https
    deploy_systemd_services
    setup_ssh_keys
    setup_backups
    setup_monitoring
    setup_log_rotation
    setup_firewall
    create_env_file
    start_services
    run_security_scan

    print_summary
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --user)
            DEPLOY_USER="$2"
            DEPLOY_DIR="/home/$2/ai-employee"
            shift 2
            ;;
        --dir)
            DEPLOY_DIR="$2"
            DEPLOY_USER=$(basename "$(dirname "$2")")
            shift 2
            ;;
        --odoo-dir)
            ODOO_DIR="$2"
            shift 2
            ;;
        --domain)
            DOMAIN_NAME="$2"
            shift 2
            ;;
        --payment-threshold)
            PAYMENT_APPROVAL_THRESHOLD="$2"
            shift 2
            ;;
        --email-threshold)
            EMAIL_BULK_THRESHOLD="$2"
            shift 2
            ;;
        --skip-odoo)
            SKIP_ODOO=true
            shift
            ;;
        --skip-services)
            SKIP_SERVICES=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --user USERNAME         Deploy as specified user (default: oracle)"
            echo "  --dir PATH              Deploy to specified directory"
            echo "  --odoo-dir PATH         Odoo installation directory"
            echo "  --domain DOMAIN         Domain name for HTTPS"
            echo "  --payment-threshold N   Payment approval threshold (default: 100)"
            echo "  --email-threshold N     Bulk email approval threshold (default: 50)"
            echo "  --skip-odoo             Skip Odoo installation"
            echo "  --skip-services         Skip starting services after deploy"
            echo "  --help, -h              Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

main
