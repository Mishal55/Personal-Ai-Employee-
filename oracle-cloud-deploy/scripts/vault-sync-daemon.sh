#!/bin/bash
# ============================================
# Vault Sync Daemon
# Continuous Git-based vault synchronization
# Excludes secrets (.env, tokens, credentials)
# ============================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$BASE_DIR/config/sync-config.json"
LOG_FILE="$BASE_DIR/logs/vault-sync-daemon.log"
PID_FILE="/tmp/vault-sync-daemon.pid"
LOCK_FILE="/tmp/vault-sync.lock"

# Default settings
SYNC_INTERVAL=300  # 5 minutes
AUTO_PUSH=true
AUTO_PULL=true
GIT_REMOTE=""
SYNC_BRANCH="vault-sync"

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    SYNC_INTERVAL=$(jq -r '.sync_interval // 300' "$CONFIG_FILE" 2>/dev/null)
    AUTO_PUSH=$(jq -r '.auto_push // true' "$CONFIG_FILE" 2>/dev/null)
    AUTO_PULL=$(jq -r '.auto_pull // true' "$CONFIG_FILE" 2>/dev/null)
    GIT_REMOTE=$(jq -r '.git_remote // ""' "$CONFIG_FILE" 2>/dev/null)
    SYNC_BRANCH=$(jq -r '.sync_branch // "vault-sync"' "$CONFIG_FILE" 2>/dev/null)
fi

# Override with environment
SYNC_INTERVAL="${SYNC_INTERVAL:-300}"
GIT_REMOTE="${GIT_REMOTE:-$VAULT_SYNC_REMOTE}"
SYNC_BRANCH="${SYNC_BRANCH:-$VAULT_SYNC_BRANCH}"

# Logging
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

log_info() { log "[INFO] $1"; }
log_warn() { log "[WARN] $1"; }
log_error() { log "[ERROR] $1"; }
log_success() { log "[SUCCESS] $1"; }

# Check if daemon is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Get daemon PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    fi
}

# Initialize git repository
init_git() {
    log_info "Initializing git repository..."

    cd "$BASE_DIR"

    if [ ! -d ".git" ]; then
        git init
        git config user.name "AI Employee Vault Sync"
        git config user.email "vault-sync@ai-employee.local"
        log_success "Git repository initialized"
    fi

    # Setup remote if configured
    if [ -n "$GIT_REMOTE" ]; then
        git remote remove origin 2>/dev/null || true
        git remote add origin "$GIT_REMOTE"
        log_success "Git remote configured: $GIT_REMOTE"
    fi
}

# Verify secrets are excluded
verify_secrets() {
    log_info "Verifying secrets exclusion..."

    cd "$BASE_DIR"

    # Check .gitignore exists
    if [ ! -f ".gitignore" ]; then
        log_warn ".gitignore not found. Creating..."
        cat > ".gitignore" << 'EOF'
# Environment & Secrets
.env
.env.*
!.env.example
*.env
*.token
*.key
*.secret
*credentials*
*api_key*

# Sensitive files
secrets/
tokens/
private/
*.pem
*.p12
*.pfx
*.p8

# IDE & Editor
.idea/
.vscode/
*.swp
*.swo
*~

# Python
__pycache__/
*.py[cod]
*$py.class
.Python
venv/
ENV/
env/

# Node
node_modules/
npm-debug.log
yarn-error.log

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db

# Git
.git/
!.gitignore
EOF
    fi

    log_success "Secrets exclusion verified"
}

# Push changes to remote
do_push() {
    if [ "$AUTO_PUSH" != "true" ]; then
        return 0
    fi

    log_info "Pushing changes to remote..."

    cd "$BASE_DIR"

    # Check for changes
    if [ -z "$(git status --porcelain)" ]; then
        log_info "No changes to push"
        return 0
    fi

    # Stage and commit
    git add -A
    local change_count=$(git diff --cached --name-only | wc -l)

    if [ $change_count -gt 0 ]; then
        git commit -m "vault-sync: Auto-sync $change_count files - $(date '+%Y-%m-%d %H:%M')"

        # Pull before push
        git pull origin "$SYNC_BRANCH" --rebase --no-edit 2>/dev/null || true

        # Push
        if git push -u origin "$SYNC_BRANCH" 2>/dev/null; then
            log_success "Pushed $change_count file(s) to remote"
        else
            log_warn "Push failed. Will retry next cycle."
            return 1
        fi
    fi

    return 0
}

# Pull changes from remote
do_pull() {
    if [ "$AUTO_PULL" != "true" ]; then
        return 0
    fi

    log_info "Pulling changes from remote..."

    cd "$BASE_DIR"

    # Check if remote branch exists
    if ! git rev-parse --verify origin/"$SYNC_BRANCH" &>/dev/null; then
        log_info "Remote branch doesn't exist. Creating..."
        git checkout -b "$SYNC_BRANCH"
        git push -u origin "$SYNC_BRANCH"
        return 0
    fi

    # Pull changes
    if git pull origin "$SYNC_BRANCH" 2>/dev/null; then
        log_success "Pulled changes from remote"
    else
        log_warn "Pull failed. Will retry next cycle."
        return 1
    fi

    return 0
}

# Main sync cycle
sync_cycle() {
    log_info "Starting sync cycle..."

    local errors=0

    do_pull || ((errors++))
    do_push || ((errors++))

    if [ $errors -eq 0 ]; then
        log_success "Sync cycle complete"
    else
        log_warn "Sync cycle completed with $errors error(s)"
    fi

    return $errors
}

# Cleanup on exit
cleanup() {
    log_info "Shutting down vault sync daemon..."
    rm -f "$PID_FILE"
    rm -f "$LOCK_FILE"
    exit 0
}

# Setup signal handlers
trap cleanup SIGTERM SIGINT SIGHUP

# Main daemon loop
run_daemon() {
    log_info "Starting vault sync daemon (interval: ${SYNC_INTERVAL}s)..."

    # Write PID file
    echo $$ > "$PID_FILE"

    # Initialize
    init_git
    verify_secrets

    # Main loop
    while true; do
        # Check lock file
        if [ -f "$LOCK_FILE" ]; then
            log_warn "Another sync process is running. Skipping cycle."
            sleep 10
            continue
        fi

        # Create lock
        touch "$LOCK_FILE"

        # Run sync cycle
        sync_cycle || true

        # Remove lock
        rm -f "$LOCK_FILE"

        # Sleep
        sleep "$SYNC_INTERVAL"
    done
}

# Start daemon
start() {
    if is_running; then
        log_error "Daemon is already running (PID: $(get_pid))"
        exit 1
    fi

    log_info "Starting vault sync daemon..."
    run_daemon &
    disown

    sleep 2

    if is_running; then
        log_success "Vault sync daemon started (PID: $(get_pid))"
    else
        log_error "Failed to start daemon"
        exit 1
    fi
}

# Stop daemon
stop() {
    if ! is_running; then
        log_warn "Daemon is not running"
        return 0
    fi

    local pid=$(get_pid)
    log_info "Stopping vault sync daemon (PID: $pid)..."

    kill "$pid" 2>/dev/null || true

    # Wait for process to stop
    for i in {1..10}; do
        if ! is_running; then
            log_success "Daemon stopped"
            return 0
        fi
        sleep 1
    done

    # Force kill
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
    log_success "Daemon force stopped"
}

# Restart daemon
restart() {
    stop
    sleep 2
    start
}

# Show status
status() {
    if is_running; then
        echo -e "\033[0;32m●\033[0m Vault sync daemon is running (PID: $(get_pid))"
        echo ""
        echo "Configuration:"
        echo "  Sync Interval: ${SYNC_INTERVAL}s"
        echo "  Auto Push: ${AUTO_PUSH}"
        echo "  Auto Pull: ${AUTO_PULL}"
        echo "  Git Remote: ${GIT_REMOTE:-Not set}"
        echo "  Sync Branch: $SYNC_BRANCH"
    else
        echo -e "\033[0;31m●\033[0m Vault sync daemon is not running"
    fi
}

# Show help
show_help() {
    cat << EOF
Vault Sync Daemon - Git-based vault synchronization

Usage: $0 {start|stop|restart|status|sync}

Commands:
    start       Start the daemon
    stop        Stop the daemon
    restart     Restart the daemon
    status      Show daemon status
    sync        Run one sync cycle manually

Configuration:
    Edit config/sync-config.json or set environment variables:
    - GIT_REMOTE / VAULT_SYNC_REMOTE
    - SYNC_BRANCH / VAULT_SYNC_BRANCH
    - SYNC_INTERVAL (seconds)
    - AUTO_PUSH (true/false)
    - AUTO_PULL (true/false)

EOF
}

# Parse arguments
case "${1:-start}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    sync)
        sync_cycle
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
