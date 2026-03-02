#!/bin/bash
# =============================================================================
# Odoo Community Production Deployment with Backups and Monitoring
# =============================================================================

set -e

echo "=========================================="
echo "Odoo Production Deployment"
echo "=========================================="

# Configuration
ODOO_USER="odoo"
ODOO_DB="odoo"
ODOO_ADMIN_PASSWORD=$(openssl rand -base64 32)
BACKUP_DIR="/backups/odoo"
MONITORING_DIR="/opt/monitoring"

log_info() {
    echo -e "\033[0;32m[INFO]\033[0m $1"
}

# =============================================================================
# Step 1: Install Dependencies
# =============================================================================
log_info "Step 1: Installing dependencies..."
apt update && apt upgrade -y
apt install -y \
    postgresql \
    postgresql-contrib \
    python3 \
    python3-pip \
    python3-venv \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    supervisor \
    wkhtmltopdf \
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev

# =============================================================================
# Step 2: Configure PostgreSQL
# =============================================================================
log_info "Step 2: Configuring PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

sudo -u postgres createuser -s ${ODOO_USER}
sudo -u postgres createdb ${ODOO_DB} -O ${ODOO_USER}

# Set PostgreSQL password
sudo -u postgres psql -c "ALTER USER ${ODOO_USER} WITH PASSWORD 'odoo_secure_password';"

# =============================================================================
# Step 3: Download and Install Odoo
# =============================================================================
log_info "Step 3: Installing Odoo..."

# Create Odoo user
useradd -m -d /opt/odoo -U -r -s /bin/bash ${ODOO_USER}

# Download Odoo
wget -q https://github.com/odoo/odoo/archive/refs/heads/16.0.tar.gz -O /tmp/odoo.tar.gz
tar -xzf /tmp/odoo.tar.gz -C /opt/odoo --strip-components=1
chown -R ${ODOO_USER}:${ODOO_USER} /opt/odoo

# Install Python dependencies
pip3 install -r /opt/odoo/requirements.txt

# =============================================================================
# Step 4: Configure Odoo
# =============================================================================
log_info "Step 4: Configuring Odoo..."

cat > /etc/odoo.conf << EOF
[options]
admin_passwd = ${ODOO_ADMIN_PASSWORD}
db_host = localhost
db_port = 5432
db_user = ${ODOO_USER}
db_password = odoo_secure_password
db_name = ${ODOO_DB}
addons_path = /opt/odoo/addons,/opt/odoo/odoo/addons
http_port = 8069
logfile = /var/log/odoo/odoo-server.log
log_level = info
data_dir = /var/lib/odoo
EOF

mkdir -p /var/log/odoo /var/lib/odoo
chown -R ${ODOO_USER}:${ODOO_USER} /var/log/odoo /var/lib/odoo

# =============================================================================
# Step 5: Create Systemd Service
# =============================================================================
log_info "Step 5: Creating systemd service..."

cat > /etc/systemd/system/odoo.service << EOF
[Unit]
Description=Odoo
After=network.target postgresql.service

[Service]
Type=simple
User=${ODOO_USER}
Group=${ODOO_USER}
ExecStart=/usr/bin/python3 /opt/odoo/odoo-bin -c /etc/odoo.conf
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable odoo
systemctl start odoo

# =============================================================================
# Step 6: Configure Nginx Reverse Proxy
# =============================================================================
log_info "Step 6: Configuring Nginx..."

cat > /etc/nginx/sites-available/odoo << EOF
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Client body size limit (for attachments)
    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8069;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
    }

    location /longpolling {
        proxy_pass http://127.0.0.1:8072;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static/ {
        alias /var/www/odoo/static/;
        expires max;
        add_header Cache-Control "public, immutable";
    }
}
EOF

ln -sf /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# =============================================================================
# Step 7: Setup Automated Backups
# =============================================================================
log_info "Step 7: Setting up automated backups..."

mkdir -p ${BACKUP_DIR}

cat > /usr/local/bin/odoo-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/odoo"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="odoo"
ODOO_USER="odoo"

echo "Starting Odoo backup: ${DATE}"

# Database backup
echo "Backing up database..."
sudo -u postgres pg_dump ${DB_NAME} | gzip > ${BACKUP_DIR}/db_${DATE}.sql.gz

# Filestore backup
echo "Backing up filestore..."
tar -czf ${BACKUP_DIR}/filestore_${DATE}.tar.gz /var/lib/odoo/filestore/

# Config backup
echo "Backing up configuration..."
cp /etc/odoo.conf ${BACKUP_DIR}/config_${DATE}.conf

# Verify backups
echo "Verifying backups..."
ls -lh ${BACKUP_DIR}/ | tail -5

# Cleanup old backups (keep 7 days)
echo "Cleaning up old backups..."
find ${BACKUP_DIR} -name "*.gz" -mtime +7 -delete
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +7 -delete
find ${BACKUP_DIR} -name "*.conf" -mtime +7 -delete

echo "Backup completed successfully: ${DATE}"

# Log backup
echo "$(date -Iseconds) - Backup completed: ${DATE}" >> /var/log/odoo/backups.log
EOF

chmod +x /usr/local/bin/odoo-backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/odoo-backup.sh") | crontab -

# =============================================================================
# Step 8: Setup Monitoring
# =============================================================================
log_info "Step 8: Setting up monitoring..."

mkdir -p ${MONITORING_DIR}

# Health check script
cat > ${MONITORING_DIR}/health_check.sh << 'EOF'
#!/bin/bash
TIMESTAMP=$(date -Iseconds)
STATUS_FILE="/var/log/odoo/health_status.json"

# Check Odoo service
if systemctl is-active --quiet odoo; then
    ODOO_STATUS="healthy"
else
    ODOO_STATUS="unhealthy"
fi

# Check PostgreSQL
if systemctl is-active --quiet postgresql; then
    DB_STATUS="healthy"
else
    DB_STATUS="unhealthy"
fi

# Check Nginx
if systemctl is-active --quiet nginx; then
    NGINX_STATUS="healthy"
else
    NGINX_STATUS="unhealthy"
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 80 ]; then
    DISK_STATUS="healthy"
elif [ "$DISK_USAGE" -lt 90 ]; then
    DISK_STATUS="warning"
else
    DISK_STATUS="critical"
fi

# Generate status JSON
cat > ${STATUS_FILE} << STATUSEOF
{
    "timestamp": "${TIMESTAMP}",
    "services": {
        "odoo": "${ODOO_STATUS}",
        "postgresql": "${DB_STATUS}",
        "nginx": "${NGINX_STATUS}"
    },
    "disk": {
        "status": "${DISK_STATUS}",
        "usage_percent": ${DISK_USAGE}
    }
}
STATUSEOF

# Output status
cat ${STATUS_FILE}

# Exit with error if any service is unhealthy
if [ "$ODOO_STATUS" != "healthy" ] || [ "$DB_STATUS" != "healthy" ] || [ "$NGINX_STATUS" != "healthy" ]; then
    exit 1
fi

exit 0
EOF

chmod +x ${MONITORING_DIR}/health_check.sh

# Add health check to crontab (every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * ${MONITORING_DIR}/health_check.sh") | crontab -

# =============================================================================
# Step 9: Setup Log Rotation
# =============================================================================
log_info "Step 9: Configuring log rotation..."

cat > /etc/logrotate.d/odoo << 'EOF'
/var/log/odoo/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 odoo odoo
    sharedscripts
    postrotate
        systemctl reload odoo > /dev/null 2>&1 || true
    endscript
}
EOF

# =============================================================================
# Step 10: Display Summary
# =============================================================================
echo ""
echo "=========================================="
echo "Odoo Installation Complete!"
echo "=========================================="
echo ""
echo "Access Odoo at: http://$(hostname -I | awk '{print $1}'):8069"
echo ""
echo "IMPORTANT - Save these credentials:"
echo "  Admin Password: ${ODOO_ADMIN_PASSWORD}"
echo "  Database: ${ODOO_DB}"
echo "  Database User: ${ODOO_USER}"
echo ""
echo "Commands:"
echo "  - Status: systemctl status odoo"
echo "  - Logs: tail -f /var/log/odoo/odoo-server.log"
echo "  - Backup: /usr/local/bin/odoo-backup.sh"
echo "  - Health: ${MONITORING_DIR}/health_check.sh"
echo ""
echo "Backup Schedule: Daily at 2:00 AM"
echo "Health Check: Every 5 minutes"
echo ""
