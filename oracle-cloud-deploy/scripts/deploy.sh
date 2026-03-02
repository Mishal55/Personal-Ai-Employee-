#!/bin/bash
# ============================================
# Oracle Cloud VM Deployment Script
# Deploys AI Employee services with 24/7 watchers
# ============================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_USER="${DEPLOY_USER:-oracle}"
DEPLOY_DIR="${DEPLOY_DIR:-/home/${DEPLOY_USER}/ai-employee}"
SYSTEMD_DIR="/etc/systemd/system"
LOG_DIR="/var/log/ai-employee"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root"
        log_info "Usage: sudo ./deploy.sh"
        exit 1
    fi
}

# Detect Oracle Cloud Linux version
detect_os() {
    log_info "Detecting operating system..."
    
    if [ -f /etc/oracle-release ]; then
        OS_VERSION=$(cat /etc/oracle-release)
        log_info "Detected: $OS_VERSION"
        OS_TYPE="oracle"
    elif [ -f /etc/os-release ]; then
        source /etc/os-release
        OS_VERSION="$PRETTY_NAME"
        if [[ "$ID" == "ubuntu" ]]; then
            OS_TYPE="ubuntu"
        elif [[ "$ID" == "ol" ]]; then
            OS_TYPE="oracle"
        else
            OS_TYPE="unknown"
        fi
        log_info "Detected: $OS_VERSION ($OS_TYPE)"
    else
        log_error "Could not detect OS version"
        exit 1
    fi
}

# Update system packages
update_system() {
    log_step "Updating system packages..."
    
    if command -v apt &> /dev/null; then
        apt update
        apt upgrade -y
    elif command -v yum &> /dev/null; then
        yum update -y
    elif command -v dnf &> /dev/null; then
        dnf update -y
    fi
    
    log_success "System packages updated"
}

# Install required packages
install_packages() {
    log_step "Installing required packages..."
    
    local packages=(
        git
        python3
        python3-pip
        python3-venv
        nodejs
        npm
        curl
        wget
        jq
        htop
        iotop
        net-tools
        unzip
        zip
    )
    
    if command -v apt &> /dev/null; then
        apt install -y "${packages[@]}"
    elif command -v yum &> /dev/null; then
        yum install -y "${packages[@]}"
    elif command -v dnf &> /dev/null; then
        dnf install -y "${packages[@]}"
    fi
    
    log_success "Required packages installed"
}

# Create deployment user if not exists
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
    
    log_success "Deployment user configured"
}

# Create deployment directory structure
create_directories() {
    log_step "Creating directory structure..."
    
    # Create main deployment directory
    mkdir -p "$DEPLOY_DIR"
    
    # Create subdirectories
    mkdir -p "$DEPLOY_DIR"/{scripts,services,config,logs,data,vault}
    mkdir -p "$DEPLOY_DIR"/vault/{Needs_Action,Done,Pending_Approval,Briefings}
    mkdir -p "$DEPLOY_DIR"/mcp-servers
    mkdir -p "$LOG_DIR"
    
    # Set ownership
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$LOG_DIR"
    
    # Set permissions
    chmod 755 "$DEPLOY_DIR"
    chmod 755 "$DEPLOY_DIR"/scripts
    chmod 700 "$DEPLOY_DIR"/config
    
    log_success "Directory structure created"
}

# Setup Python virtual environment
setup_python() {
    log_step "Setting up Python virtual environment..."
    
    cd "$DEPLOY_DIR"
    
    # Create virtual environment
    python3 -m venv venv
    
    # Activate and upgrade pip
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    
    # Install requirements if exists
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt"
    fi
    
    # Install common packages
    pip install requests python-dotenv schedule
    
    log_success "Python environment setup complete"
}

# Setup Node.js environment
setup_node() {
    log_step "Setting up Node.js environment..."
    
    cd "$DEPLOY_DIR"
    
    # Install global packages
    npm install -g nodemon pm2
    
    log_success "Node.js environment setup complete"
}

# Deploy scripts
deploy_scripts() {
    log_step "Deploying scripts..."
    
    # Copy scripts
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

# Deploy systemd services
deploy_systemd() {
    log_step "Deploying systemd services..."
    
    # Copy service files
    cp "$SCRIPT_DIR/systemd/"*.service "$SYSTEMD_DIR/"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable ai-employee-watcher.service 2>/dev/null || true
    systemctl enable ai-employee-orchestrator.service 2>/dev/null || true
    systemctl enable ai-employee-vault-sync.service 2>/dev/null || true
    
    log_success "Systemd services deployed"
}

# Setup SSH keys for vault sync
setup_ssh_keys() {
    log_step "Setting up SSH keys for vault sync..."
    
    local ssh_dir="/home/${DEPLOY_USER}/.ssh"
    
    mkdir -p "$ssh_dir"
    chown "$DEPLOY_USER:$DEPLOY_USER" "$ssh_dir"
    chmod 700 "$ssh_dir"
    
    # Generate key if not exists
    if [ ! -f "$ssh_dir/vault_sync_key" ]; then
        ssh-keygen -t ed25519 -f "$ssh_dir/vault_sync_key" -N "" -C "vault-sync@ai-employee"
        chown "$DEPLOY_USER:$DEPLOY_USER" "$ssh_dir/vault_sync_key"*
        chmod 600 "$ssh_dir/vault_sync_key"
        log_info "Generated new SSH key for vault sync"
    else
        log_info "SSH key already exists"
    fi
    
    log_success "SSH keys configured"
}

# Create environment file template
create_env_file() {
    log_step "Creating environment file..."
    
    local env_file="$DEPLOY_DIR/.env.example"
    
    cat > "$env_file" << 'EOF'
# AI Employee Environment Configuration
# Copy this file to .env and fill in your values
# DO NOT commit .env to git!

# Oracle Cloud Configuration
OCI_REGION=us-ashburn-1
OCI_COMPARTMENT_ID=

# Database Configuration
DATABASE_URL=
DATABASE_PASSWORD=

# API Keys (Add your own)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Odoo Configuration
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=

# Vault Sync Configuration
VAULT_SYNC_REMOTE=
VAULT_SYNC_BRANCH=vault-sync

# Logging
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=30

# Feature Flags
ENABLE_CEO_BRIEFING=true
ENABLE_INVOICE_PROCESSING=true
ENABLE_VAULT_SYNC=true
EOF

    chown "$DEPLOY_USER:$DEPLOY_USER" "$env_file"
    chmod 640 "$env_file"
    
    log_success "Environment file template created"
    log_warn "Copy .env.example to .env and fill in your values!"
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
EOF

    log_success "Log rotation configured"
}

# Setup firewall rules
setup_firewall() {
    log_step "Configuring firewall..."
    
    # Only open necessary ports
    if command -v firewall-cmd &> /dev/null; then
        # Oracle Linux / firewalld
        firewall-cmd --permanent --add-service=ssh 2>/dev/null || true
        firewall-cmd --permanent --add-port=8069/tcp 2>/dev/null || true  # Odoo
        firewall-cmd --reload 2>/dev/null || true
    elif command -v ufw &> /dev/null; then
        # Ubuntu / UFW
        ufw allow ssh 2>/dev/null || true
        ufw allow 8069/tcp 2>/dev/null || true
    fi
    
    log_success "Firewall configured"
}

# Start services
start_services() {
    log_step "Starting services..."
    
    systemctl start ai-employee-watcher.service 2>/dev/null || log_warn "Watcher service not started"
    systemctl start ai-employee-orchestrator.service 2>/dev/null || log_warn "Orchestrator service not started"
    systemctl start ai-employee-vault-sync.service 2>/dev/null || log_warn "Vault sync service not started"
    
    # Wait for services to start
    sleep 5
    
    # Check status
    log_info "Service status:"
    systemctl status ai-employee-watcher.service --no-pager -l 2>/dev/null || true
    systemctl status ai-employee-orchestrator.service --no-pager -l 2>/dev/null || true
    systemctl status ai-employee-vault-sync.service --no-pager -l 2>/dev/null || true
    
    log_success "Services started"
}

# Print deployment summary
print_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}    Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Deployment Directory:${NC} $DEPLOY_DIR"
    echo -e "${BLUE}Log Directory:${NC} $LOG_DIR"
    echo -e "${BLUE}User:${NC} $DEPLOY_USER"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. SSH into the VM as $DEPLOY_USER"
    echo "2. Copy and configure .env file:"
    echo "   cp $DEPLOY_DIR/.env.example $DEPLOY_DIR/.env"
    echo "   nano $DEPLOY_DIR/.env"
    echo ""
    echo "3. Configure vault sync remote:"
    echo "   cd $DEPLOY_DIR"
    echo "   ./scripts/vault-sync.sh --remote <your-git-remote> setup"
    echo ""
    echo "4. Check service status:"
    echo "   systemctl status ai-employee-*"
    echo ""
    echo "5. View logs:"
    echo "   journalctl -u ai-employee-watcher -f"
    echo ""
    echo -e "${GREEN}========================================${NC}"
}

# Main deployment function
main() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Oracle Cloud VM Deployment Script${NC}"
    echo -e "${BLUE}  AI Employee Services${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    check_root
    detect_os
    
    log_info "Starting deployment..."
    
    update_system
    install_packages
    create_user
    create_directories
    setup_python
    setup_node
    deploy_scripts
    deploy_systemd
    setup_ssh_keys
    create_env_file
    setup_log_rotation
    setup_firewall
    start_services
    
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
        --skip-services)
            SKIP_SERVICES=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --user USERNAME    Deploy as specified user (default: oracle)"
            echo "  --dir PATH         Deploy to specified directory"
            echo "  --skip-services    Skip starting services after deploy"
            echo "  --help, -h         Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

main
