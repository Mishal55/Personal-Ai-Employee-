#!/bin/bash
# =============================================================================
# AI Employee Platinum Tier - AWS EC2 Deployment Script
# =============================================================================
# Deploys AI Employee on AWS Free Tier (t2.micro/t3.micro)
# Includes: Python, Node.js, Playwright, Odoo, and all dependencies
# =============================================================================

set -e  # Exit on error

echo "=========================================="
echo "AI Employee Platinum - AWS Deployment"
echo "=========================================="

# Configuration
AI_USER="aiemployee"
VAULT_PATH="/home/${AI_USER}/AI_Employee_Vault"
SCRIPTS_PATH="/home/${AI_USER}/scripts"
ODOO_PATH="/opt/odoo"
PYTHON_VERSION="3.10"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Step 1: System Updates
# =============================================================================
log_info "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y

# =============================================================================
# Step 2: Install Core Dependencies
# =============================================================================
log_info "Step 2: Installing core dependencies..."
sudo apt install -y \
    git \
    curl \
    wget \
    vim \
    htop \
    ufw \
    fail2ban \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7 \
    libtiff5 \
    libharfbuzz0b \
    libglib2.0-0 \
    libgl1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libgtk-3-0 \
    libatspi2.0-0 \
    xvfb \
    postgresql \
    postgresql-contrib \
    nginx \
    supervisor

# =============================================================================
# Step 3: Install Node.js (for MCP servers)
# =============================================================================
log_info "Step 3: Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# =============================================================================
# Step 4: Create AI Employee User
# =============================================================================
log_info "Step 4: Creating AI Employee user..."
if ! id "${AI_USER}" &>/dev/null; then
    sudo adduser --disabled-password --gecos "" ${AI_USER}
    sudo usermod -aG sudo ${AI_USER}
fi

# =============================================================================
# Step 5: Install Python Dependencies
# =============================================================================
log_info "Step 5: Setting up Python virtual environment..."
sudo -u ${AI_USER} bash << 'EOF'
cd /home/aiemployee
python3 -m venv ai_employee_env
source ai_employee_env/bin/activate
pip install --upgrade pip
pip install playwright python-dotenv requests
playwright install chromium
playwright install-deps chromium
deactivate
EOF

# =============================================================================
# Step 6: Clone AI Employee Repository
# =============================================================================
log_info "Step 6: Cloning AI Employee repository..."
sudo -u ${AI_USER} bash << 'EOF'
cd /home/aiemployee
git clone https://github.com/yourusername/ai-employee.git .
mkdir -p AI_Employee_Vault/Inbox AI_Employee_Vault/Needs_Action AI_Employee_Vault/Plans
mkdir -p AI_Employee_Vault/Pending_Approval AI_Employee_Vault/Approved AI_Employee_Vault/Done
mkdir -p AI_Employee_Vault/Logs AI_Employee_Vault/Briefings/CEO
mkdir -p AI_Employee_Vault/watchers/whatsapp AI_Employee_Vault/watchers/linkedin
mkdir -p AI_Employee_Vault/watchers/facebook AI_Employee_Vault/watchers/instagram AI_Employee_Vault/watchers/twitter
mkdir -p AI_Employee_Vault/Accounting/Odoo
EOF

# =============================================================================
# Step 7: Install Odoo Community
# =============================================================================
log_info "Step 7: Installing Odoo Community..."

# Create Odoo system user
sudo useradd -m -d ${ODOO_PATH} -U -r -s /bin/bash odoo

# Install Odoo dependencies
sudo apt install -y \
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libffi-dev \
    libssl-dev \
    node-less \
    npm \
    rtlcss

# Download and install Odoo
sudo wget -O - https://nightly.odoo.com/16.0/odoo-nightly.gpg | sudo apt-key add -
echo "deb http://nightly.odoo.com/16.0/nightly/deb/ ./" | sudo tee /etc/apt/sources.list.d/odoo.list
sudo apt update
sudo apt install -y odoo

# Configure PostgreSQL for Odoo
sudo -u postgres createuser -s odoo
sudo -u postgres createuser -s ${AI_USER}

# =============================================================================
# Step 8: Configure Firewall (UFW)
# =============================================================================
log_info "Step 8: Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 8069/tcp  # Odoo
sudo ufw allow 8072/tcp  # Odoo (alternative)
sudo ufw --force enable

# =============================================================================
# Step 9: Configure Fail2Ban
# =============================================================================
log_info "Step 9: Configuring Fail2Ban..."
sudo cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
EOF

sudo systemctl restart fail2ban

# =============================================================================
# Step 10: Create Systemd Services
# =============================================================================
log_info "Step 10: Creating systemd services..."

# AI Employee Scheduler Service
sudo cat > /etc/systemd/system/ai-employee-scheduler.service << EOF
[Unit]
Description=AI Employee Scheduler
After=network.target

[Service]
Type=simple
User=${AI_USER}
WorkingDirectory=/home/${AI_USER}
Environment="PATH=/home/${AI_USER}/ai_employee_env/bin"
Environment="AI_VAULT_PATH=${VAULT_PATH}"
Environment="AI_SCRIPTS_PATH=${SCRIPTS_PATH}"
ExecStart=/home/${AI_USER}/ai_employee_env/bin/python /home/${AI_USER}/scripts/scheduler.py --run
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Ralph Wiggum Loop Service
sudo cat > /etc/systemd/system/ai-employee-ralph.service << EOF
[Unit]
Description=Ralph Wiggum Autonomous Loop
After=network.target

[Service]
Type=simple
User=${AI_USER}
WorkingDirectory=/home/${AI_USER}
Environment="PATH=/home/${AI_USER}/ai_employee_env/bin"
Environment="AI_VAULT_PATH=${VAULT_PATH}"
ExecStart=/home/${AI_USER}/ai_employee_env/bin/python /home/${AI_USER}/scripts/ralph_wiggum_loop.py --continuous --interval 300
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Odoo Service (already exists, but ensuring it's enabled)
sudo systemctl enable odoo
sudo systemctl start odoo

# Reload and start services
sudo systemctl daemon-reload
sudo systemctl enable ai-employee-scheduler
sudo systemctl enable ai-employee-ralph
sudo systemctl start ai-employee-scheduler
sudo systemctl start ai-employee-ralph

# =============================================================================
# Step 11: Configure Nginx Reverse Proxy
# =============================================================================
log_info "Step 11: Configuring Nginx..."
sudo cat > /etc/nginx/sites-available/ai-employee << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/odoo/static/;
        expires max;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/ai-employee /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# =============================================================================
# Step 12: Setup Automated Backups
# =============================================================================
log_info "Step 12: Setting up automated backups..."

# Create backup script
sudo cat > /usr/local/bin/odoo-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/odoo"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="odoo"

mkdir -p ${BACKUP_DIR}

# Database backup
sudo -u postgres pg_dump ${DB_NAME} | gzip > ${BACKUP_DIR}/db_${DATE}.sql.gz

# Filestore backup
tar -czf ${BACKUP_DIR}/filestore_${DATE}.tar.gz /var/lib/odoo/filestore/

# Keep only last 7 days
find ${BACKUP_DIR} -name "*.gz" -mtime +7 -delete
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: ${DATE}"
EOF

sudo chmod +x /usr/local/bin/odoo-backup.sh
sudo mkdir -p /backups/odoo
sudo chown ${AI_USER}:${AI_USER} /backups

# Add cron job for daily backups
(sudo crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/odoo-backup.sh") | sudo crontab -

# =============================================================================
# Step 13: Setup Monitoring Script
# =============================================================================
log_info "Step 13: Setting up monitoring..."

sudo cat > /usr/local/bin/ai-employee-monitor.sh << 'EOF'
#!/bin/bash
echo "=== AI Employee System Status ==="
echo "Time: $(date)"
echo ""
echo "=== Disk Usage ==="
df -h /
echo ""
echo "=== Memory Usage ==="
free -h
echo ""
echo "=== AI Employee Services ==="
systemctl status ai-employee-scheduler --no-pager -l
systemctl status ai-employee-ralph --no-pager -l
echo ""
echo "=== Odoo Service ==="
systemctl status odoo --no-pager -l
echo ""
echo "=== Recent Logs ==="
tail -20 /var/log/odoo/odoo-server.log
EOF

sudo chmod +x /usr/local/bin/ai-employee-monitor.sh

# =============================================================================
# Step 14: Final Configuration
# =============================================================================
log_info "Step 14: Final configuration..."

# Create environment file template
sudo -u ${AI_USER} bash << 'EOF'
cat > /home/aiemployee/.env << 'ENVEOF'
# AI Employee Environment Configuration
AI_VAULT_PATH=/home/aiemployee/AI_Employee_Vault
AI_SCRIPTS_PATH=/home/aiemployee/scripts

# Odoo Configuration
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=CHANGE_ME_IN_PRODUCTION
ODOO_COMPANY_ID=1

# Social Media (Add your tokens)
FACEBOOK_PAGE_ID=
FACEBOOK_ACCESS_TOKEN=
INSTAGRAM_BUSINESS_ACCOUNT_ID=
INSTAGRAM_ACCESS_TOKEN=
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=
ENVEOF
chmod 600 /home/aiemployee/.env
EOF

# Set proper permissions
sudo chown -R ${AI_USER}:${AI_USER} /home/${AI_USER}
sudo chmod 755 /home/${AI_USER}

# =============================================================================
# Step 15: Display Summary
# =============================================================================
echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "AI Employee is now running on this server."
echo ""
echo "Access Points:"
echo "  - Odoo: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'YOUR_SERVER_IP'):8069"
echo "  - Nginx: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'YOUR_SERVER_IP')"
echo ""
echo "Important Commands:"
echo "  - Monitor: sudo /usr/local/bin/ai-employee-monitor.sh"
echo "  - Backup: sudo /usr/local/bin/odoo-backup.sh"
echo "  - Logs: tail -f /var/log/odoo/odoo-server.log"
echo "  - Services: systemctl status ai-employee-*"
echo ""
echo "Next Steps:"
echo "  1. Update .env file with your credentials"
echo "  2. Configure vault sync (see platinum/sync/README.md)"
echo "  3. Setup SSL certificate (recommended)"
echo "  4. Test all services"
echo ""
