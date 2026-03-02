#!/bin/bash
# =============================================================================
# AI Employee Platinum Tier - Oracle Cloud Free Tier Deployment
# =============================================================================
# Deploys AI Employee on Oracle Cloud Always Free (VM.Standard.A1.Flex)
# ARM-based instance with up to 24GB RAM
# =============================================================================

set -e

echo "=========================================="
echo "AI Employee Platinum - Oracle Cloud Deployment"
echo "=========================================="

# Configuration
AI_USER="aiemployee"
VAULT_PATH="/home/${AI_USER}/AI_Employee_Vault"
ODOO_PATH="/opt/odoo"

log_info() {
    echo -e "\033[0;32m[INFO]\033[0m $1"
}

# =============================================================================
# Step 1: System Updates
# =============================================================================
log_info "Step 1: Updating system packages..."
sudo dnf update -y

# =============================================================================
# Step 2: Install Core Dependencies
# =============================================================================
log_info "Step 2: Installing dependencies..."
sudo dnf install -y \
    git \
    curl \
    wget \
    vim \
    htop \
    firewalld \
    fail2ban \
    python3 \
    python3-pip \
    python3-devel \
    gcc \
    gcc-c++ \
    postgresql \
    postgresql-server \
    postgresql-contrib \
    nginx \
    supervisor \
    libxml2 \
    libxml2-devel \
    libxslt \
    libxslt-devel \
    libffi-devel \
    openssl-devel \
    bzip2-devel \
    zlib-devel \
    ncurses-devel \
    sqlite-devel \
    readline-devel \
    tk-devel \
    gdbm-devel \
    db4-devel \
    libpcap-devel \
    xz-devel \
    libjpeg-devel \
    freetype-devel \
    lcms2-devel \
    libwebp-devel \
    tcl-devel \
    tk-devel

# =============================================================================
# Step 3: Install Node.js
# =============================================================================
log_info "Step 3: Installing Node.js..."
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo dnf install -y nodejs

# =============================================================================
# Step 4: Create AI Employee User
# =============================================================================
log_info "Step 4: Creating AI Employee user..."
if ! id "${AI_USER}" &>/dev/null; then
    sudo useradd -m -d /home/${AI_USER} -s /bin/bash ${AI_USER}
fi

# =============================================================================
# Step 5: Install Python Dependencies
# =============================================================================
log_info "Step 5: Setting up Python environment..."
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
mkdir -p AI_Employee_Vault/{Inbox,Needs_Action,Plans,Pending_Approval,Approved,Done,Logs,Briefings/CEO}
mkdir -p AI_Employee_Vault/watchers/{whatsapp,linkedin,facebook,instagram,twitter}
mkdir -p AI_Employee_Vault/Accounting/Odoo
EOF

# =============================================================================
# Step 7: Install and Configure Odoo
# =============================================================================
log_info "Step 7: Installing Odoo..."

# Initialize PostgreSQL
sudo postgresql-setup --initdb --unit postgresql
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Create Odoo user and database
sudo -u postgres createuser -s odoo
sudo -u postgres createuser -s ${AI_USER}
sudo -u postgres createdb odoo -O odoo

# Download Odoo
sudo mkdir -p ${ODOO_PATH}
sudo chown ${AI_USER}:${AI_USER} ${ODOO_PATH}
sudo wget -q https://github.com/odoo/odoo/archive/refs/heads/16.0.tar.gz -O /tmp/odoo.tar.gz
sudo tar -xzf /tmp/odoo.tar.gz -C ${ODOO_PATH} --strip-components=1

# Install Odoo Python dependencies
sudo -u ${AI_USER} bash << 'EOF'
source /home/aiemployee/ai_employee_env/bin/activate
pip install -r /opt/odoo/requirements.txt
deactivate
EOF

# Create Odoo configuration
sudo cat > /etc/odoo.conf << EOF
[options]
admin_passwd = admin
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
db_name = odoo
addons_path = /opt/odoo/addons,/opt/odoo/odoo/addons
http_port = 8069
logfile = /var/log/odoo/odoo-server.log
log_level = info
EOF

sudo mkdir -p /var/log/odoo
sudo chown ${AI_USER}:${AI_USER} /var/log/odoo

# Create systemd service for Odoo
sudo cat > /etc/systemd/system/odoo.service << EOF
[Unit]
Description=Odoo
After=network.target postgresql.service

[Service]
Type=simple
User=${AI_USER}
Group=${AI_USER}
ExecStart=/home/${AI_USER}/ai_employee_env/bin/python /opt/odoo/odoo-bin -c /etc/odoo.conf
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# =============================================================================
# Step 8: Configure Firewall
# =============================================================================
log_info "Step 8: Configuring firewall..."
sudo systemctl enable firewalld
sudo systemctl start firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=8069/tcp
sudo firewall-cmd --reload

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
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# =============================================================================
# Step 10: Create AI Employee Services
# =============================================================================
log_info "Step 10: Creating systemd services..."

sudo cat > /etc/systemd/system/ai-employee-ralph.service << EOF
[Unit]
Description=Ralph Wiggum Loop
After=network.target

[Service]
Type=simple
User=${AI_USER}
WorkingDirectory=/home/${AI_USER}
Environment="PATH=/home/${AI_USER}/ai_employee_env/bin"
Environment="AI_VAULT_PATH=${VAULT_PATH}"
ExecStart=/home/${AI_USER}/ai_employee_env/bin/python /home/${AI_USER}/scripts/ralph_wiggum_loop.py --continuous --interval 300
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable odoo
sudo systemctl enable ai-employee-ralph
sudo systemctl start odoo
sudo systemctl start ai-employee-ralph

# =============================================================================
# Step 11: Setup Backups
# =============================================================================
log_info "Step 11: Setting up backups..."

sudo cat > /usr/local/bin/odoo-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/odoo"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p ${BACKUP_DIR}
sudo -u postgres pg_dump odoo | gzip > ${BACKUP_DIR}/db_${DATE}.sql.gz
echo "Backup completed: ${DATE}"
EOF

sudo chmod +x /usr/local/bin/odoo-backup.sh
(sudo crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/odoo-backup.sh") | sudo crontab -

# =============================================================================
# Step 12: Create Environment File
# =============================================================================
log_info "Step 12: Creating environment file..."

sudo -u ${AI_USER} bash << 'EOF'
cat > /home/aiemployee/.env << 'ENVEOF'
AI_VAULT_PATH=/home/aiemployee/AI_Employee_Vault
AI_SCRIPTS_PATH=/home/aiemployee/scripts
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=CHANGE_ME
ENVEOF
chmod 600 /home/aiemployee/.env
EOF

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Access Odoo at: http://YOUR_SERVER_IP:8069"
echo ""
echo "Commands:"
echo "  - Status: systemctl status odoo ai-employee-ralph"
echo "  - Logs: tail -f /var/log/odoo/odoo-server.log"
echo "  - Backup: /usr/local/bin/odoo-backup.sh"
echo ""
