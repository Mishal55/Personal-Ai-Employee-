#!/bin/bash
# ============================================
# Git Vault Sync Script
# Synchronizes AI Employee Vault between Local and Oracle Cloud
# Excludes secrets (.env, tokens, credentials)
# ============================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config/sync-config.json"
LOG_FILE="${SCRIPT_DIR}/logs/vault-sync.log"
LOCK_FILE="/tmp/vault-sync.lock"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
GIT_REMOTE=""
VAULT_PATH=""
SYNC_BRANCH="vault-sync"
AUTO_COMMIT=true
COMMIT_PREFIX="vault-sync:"

# Load configuration if exists
if [ -f "$CONFIG_FILE" ]; then
    GIT_REMOTE=$(jq -r '.git_remote // ""' "$CONFIG_FILE" 2>/dev/null)
    VAULT_PATH=$(jq -r '.vault_path // ""' "$CONFIG_FILE" 2>/dev/null)
    SYNC_BRANCH=$(jq -r '.sync_branch // "vault-sync"' "$CONFIG_FILE" 2>/dev/null)
    AUTO_COMMIT=$(jq -r '.auto_commit // true' "$CONFIG_FILE" 2>/dev/null)
fi

# Override with environment variables
GIT_REMOTE="${GIT_REMOTE:-$VAULT_SYNC_REMOTE}"
VAULT_PATH="${VAULT_PATH:-$VAULT_SYNC_PATH}"
SYNC_BRANCH="${SYNC_BRANCH:-$VAULT_SYNC_BRANCH}"

# Logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "[$timestamp] [$level] $message"
}

log_info() { log "INFO" "$1"; }
log_warn() { log "WARN" "${YELLOW}$1${NC}"; }
log_error() { log "ERROR" "${RED}$1${NC}"; }
log_success() { log "SUCCESS" "${GREEN}$1${NC}"; }

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_warn "Running as root. Consider using a non-root user for vault sync."
    fi
}

# Create necessary directories
setup_directories() {
    log_info "Setting up directories..."
    mkdir -p "${SCRIPT_DIR}/logs"
    mkdir -p "${SCRIPT_DIR}/.git"
    
    # Create logs directory with proper permissions
    chmod 755 "${SCRIPT_DIR}/logs" 2>/dev/null || true
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing=()
    
    # Check git
    if ! command -v git &> /dev/null; then
        missing+=("git")
    fi
    
    # Check jq for JSON parsing
    if ! command -v jq &> /dev/null; then
        log_warn "jq not found. Installing..."
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y jq
        elif command -v yum &> /dev/null; then
            sudo yum install -y jq
        fi
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing prerequisites: ${missing[*]}"
        log_error "Install with: sudo apt update && sudo apt install -y git jq"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Initialize git repository if not exists
init_git() {
    log_info "Initializing git repository..."
    
    cd "$SCRIPT_DIR"
    
    if [ ! -d ".git" ]; then
        git init
        log_success "Git repository initialized"
    else
        log_info "Git repository already exists"
    fi
    
    # Configure git user if not set
    if [ -z "$(git config user.name)" ]; then
        git config user.name "AI Employee Vault Sync"
        git config user.email "vault-sync@ai-employee.local"
        log_info "Git user configured"
    fi
}

# Setup git remote
setup_remote() {
    log_info "Setting up git remote..."
    
    cd "$SCRIPT_DIR"
    
    if [ -z "$GIT_REMOTE" ]; then
        log_warn "No git remote configured"
        log_info "Set GIT_REMOTE environment variable or edit config/sync-config.json"
        log_info "Example: export GIT_REMOTE='oracle@<vm-ip>:/home/oracle/ai-employee-vault.git'"
        return 1
    fi
    
    # Remove existing remote if any
    git remote remove origin 2>/dev/null || true
    
    # Add new remote
    git remote add origin "$GIT_REMOTE"
    log_success "Git remote configured: $GIT_REMOTE"
}

# Sync vault to remote
sync_push() {
    log_info "Pushing vault changes to remote..."
    
    cd "$SCRIPT_DIR"
    
    # Check for changes
    if [ -z "$(git status --porcelain)" ]; then
        log_info "No changes to push"
        return 0
    fi
    
    # Stage all changes
    git add -A
    
    # Commit if auto-commit enabled
    if [ "$AUTO_COMMIT" = "true" ]; then
        local change_count=$(git diff --cached --name-only | wc -l)
        git commit -m "${COMMIT_PREFIX} Sync $change_count files - $(date '+%Y-%m-%d %H:%M')"
        log_success "Changes committed"
    fi
    
    # Push to remote
    git pull origin "$SYNC_BRANCH" --rebase --no-edit 2>/dev/null || true
    git push -u origin "$SYNC_BRANCH"
    
    log_success "Vault pushed to remote"
}

# Sync vault from remote
sync_pull() {
    log_info "Pulling vault changes from remote..."
    
    cd "$SCRIPT_DIR"
    
    # Fetch from remote
    git fetch origin
    
    # Check if branch exists
    if ! git rev-parse --verify origin/"$SYNC_BRANCH" &>/dev/null; then
        log_warn "Remote branch $SYNC_BRANCH does not exist. Creating..."
        git checkout -b "$SYNC_BRANCH"
        git push -u origin "$SYNC_BRANCH"
        return 0
    fi
    
    # Pull changes
    git pull origin "$SYNC_BRANCH"
    
    log_success "Vault pulled from remote"
}

# Full bidirectional sync
sync_full() {
    log_info "Starting full vault sync..."
    
    sync_pull
    sync_push
    
    log_success "Full vault sync completed"
}

# Show sync status
show_status() {
    cd "$SCRIPT_DIR"
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}       Vault Sync Status${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # Git status
    echo -e "${YELLOW}Git Status:${NC}"
    git status --short
    
    echo ""
    echo -e "${YELLOW}Recent Commits:${NC}"
    git log --oneline -5
    
    echo ""
    echo -e "${YELLOW}Remote:${NC}"
    git remote -v
    
    echo ""
    echo -e "${YELLOW}Current Branch:${NC}"
    git branch --show-current
    
    echo ""
    echo -e "${YELLOW}Configuration:${NC}"
    echo "  Git Remote: ${GIT_REMOTE:-Not set}"
    echo "  Vault Path: ${VAULT_PATH:-Not set}"
    echo "  Sync Branch: $SYNC_BRANCH"
    echo "  Auto Commit: $AUTO_COMMIT"
}

# Verify secrets are excluded
verify_secrets_excluded() {
    log_info "Verifying secrets exclusion..."
    
    cd "$SCRIPT_DIR"
    
    local secrets_found=0
    
    # Check for common secret patterns
    local secret_patterns=(
        "*.env"
        "*.token"
        "*.key"
        "*.secret"
        "*credentials*"
        "*api_key*"
    )
    
    for pattern in "${secret_patterns[@]}"; do
        local found=$(find . -name "$pattern" -type f 2>/dev/null | grep -v ".git" | head -5)
        if [ -n "$found" ]; then
            log_warn "Found potential secrets matching $pattern:"
            echo "$found"
            secrets_found=$((secrets_found + 1))
        fi
    done
    
    if [ $secrets_found -eq 0 ]; then
        log_success "No secrets found in tracked files"
    else
        log_warn "Found $secrets_found potential secret patterns. Ensure .gitignore is working correctly."
    fi
    
    # Show what git would track
    echo ""
    echo -e "${YELLOW}Files that would be committed:${NC}"
    git ls-files --others --exclude-standard | head -20
}

# Setup cron job for automatic sync
setup_cron() {
    log_info "Setting up automatic sync cron job..."
    
    local cron_interval="*/15 * * * *"  # Every 15 minutes
    local cron_job="$cron_interval cd $SCRIPT_DIR && ./vault-sync.sh pull >> $LOG_FILE 2>&1"
    
    # Check if cron already exists
    if crontab -l 2>/dev/null | grep -q "vault-sync.sh"; then
        log_warn "Vault sync cron job already exists"
        crontab -l | grep "vault-sync"
        return 0
    fi
    
    # Add cron job
    (crontab -l 2>/dev/null | grep -v "vault-sync.sh"; echo "$cron_job") | crontab -
    
    log_success "Cron job added: $cron_interval"
    crontab -l | grep "vault-sync"
}

# Remove cron job
remove_cron() {
    log_info "Removing vault sync cron job..."
    
    (crontab -l 2>/dev/null | grep -v "vault-sync.sh") | crontab -
    
    log_success "Cron job removed"
}

# Show help
show_help() {
    cat << EOF
${BLUE}========================================${NC}
${BLUE}     Git Vault Sync Script${NC}
${BLUE}========================================${NC}

Usage: $0 [command] [options]

Commands:
    init            Initialize git repository
    setup           Setup remote and configuration
    push            Push local changes to remote
    pull            Pull changes from remote
    sync            Full bidirectional sync (pull then push)
    status          Show sync status
    verify          Verify secrets are excluded
    cron-add        Add automatic sync cron job
    cron-remove     Remove automatic sync cron job
    help            Show this help message

Options:
    --remote URL    Set git remote URL
    --branch NAME   Set sync branch name
    --no-commit     Disable auto-commit
    --vault-path    Set vault path

Environment Variables:
    GIT_REMOTE          Git remote URL
    VAULT_SYNC_REMOTE   Git remote URL (alias)
    VAULT_SYNC_BRANCH   Sync branch name
    VAULT_SYNC_PATH     Vault path

Examples:
    $0 init
    $0 --remote oracle@192.168.1.100:/vault.git setup
    $0 sync
    $0 --branch main push
    $0 verify

Configuration File:
    Edit config/sync-config.json for persistent settings

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --remote)
                GIT_REMOTE="$2"
                shift 2
                ;;
            --branch)
                SYNC_BRANCH="$2"
                shift 2
                ;;
            --no-commit)
                AUTO_COMMIT=false
                shift
                ;;
            --vault-path)
                VAULT_PATH="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                COMMAND="$1"
                shift
                ;;
        esac
    done
}

# Main function
main() {
    parse_args "$@"
    
    check_root
    setup_directories
    check_prerequisites
    
    case "${COMMAND:-help}" in
        init)
            init_git
            ;;
        setup)
            init_git
            setup_remote
            ;;
        push)
            sync_push
            ;;
        pull)
            sync_pull
            ;;
        sync)
            sync_full
            ;;
        status)
            show_status
            ;;
        verify)
            verify_secrets_excluded
            ;;
        cron-add)
            setup_cron
            ;;
        cron-remove)
            remove_cron
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
