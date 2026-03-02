#!/bin/bash
# ============================================
# AI Employee Health Check Script
# Comprehensive health monitoring for all services
# ============================================

set -e

# Configuration
DEPLOY_USER="${DEPLOY_USER:-oracle}"
DEPLOY_DIR="${DEPLOY_DIR:-/home/oracle/ai-employee}"
ODOO_DIR="${ODOO_DIR:-/opt/odoo}"
LOG_DIR="/var/log/ai-employee"
ODOO_LOG_DIR="/var/log/odoo"

# Thresholds
DISK_WARNING=80
DISK_CRITICAL=90
MEM_WARNING=80
MEM_CRITICAL=90
CPU_WARNING=80
CPU_CRITICAL=95

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
PASSED=0
WARNINGS=0
FAILURES=0

# Logging
log_pass() { echo -e "  ${GREEN}✓${NC} $1"; ((PASSED++)); }
log_warn() { echo -e "  ${YELLOW}⚠${NC} $1"; ((WARNINGS++)); }
log_fail() { echo -e "  ${RED}✗${NC} $1"; ((FAILURES++)); }
log_info() { echo -e "  ${BLUE}ℹ${NC} $1"; }

# Check if service is running
check_service() {
    local service=$1
    local display_name=$2

    if systemctl is-active --quiet "$service" 2>/dev/null; then
        log_pass "$display_name is running"
        return 0
    else
        log_fail "$display_name is not running"
        return 1
    fi
}

# Check HTTP endpoint
check_http() {
    local url=$1
    local name=$2
    local expected_code=${3:-200}

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")

    if [ "$http_code" = "$expected_code" ]; then
        log_pass "$name is responding (HTTP $http_code)"
        return 0
    else
        log_fail "$name is not responding (HTTP $http_code, expected $expected_code)"
        return 1
    fi
}

# Check disk usage
check_disk() {
    local mount_point=${1:-/}
    local usage=$(df -h "$mount_point" | awk 'NR==2 {print $5}' | tr -d '%')

    if [ "$usage" -ge "$DISK_CRITICAL" ]; then
        log_fail "Disk usage critical: ${usage}% on $mount_point"
        return 1
    elif [ "$usage" -ge "$DISK_WARNING" ]; then
        log_warn "Disk usage warning: ${usage}% on $mount_point"
        return 0
    else
        log_pass "Disk usage normal: ${usage}% on $mount_point"
        return 0
    fi
}

# Check memory usage
check_memory() {
    local usage=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')

    if [ "$usage" -ge "$MEM_CRITICAL" ]; then
        log_fail "Memory usage critical: ${usage}%"
        return 1
    elif [ "$usage" -ge "$MEM_WARNING" ]; then
        log_warn "Memory usage warning: ${usage}%"
        return 0
    else
        log_pass "Memory usage normal: ${usage}%"
        return 0
    fi
}

# Check CPU load
check_cpu() {
    local load=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | tr -d ' ')
    local cpu_count=$(nproc)
    local load_pct=$(echo "$load $cpu_count" | awk '{printf "%.0f", ($1/$2)*100}')

    if [ "$load_pct" -ge "$CPU_CRITICAL" ]; then
        log_fail "CPU load critical: ${load_pct}% (load: $load)"
        return 1
    elif [ "$load_pct" -ge "$CPU_WARNING" ]; then
        log_warn "CPU load warning: ${load_pct}% (load: $load)"
        return 0
    else
        log_pass "CPU load normal: ${load_pct}% (load: $load)"
        return 0
    fi
}

# Check PostgreSQL
check_postgresql() {
    if sudo -u postgres psql -c "SELECT 1" &>/dev/null; then
        log_pass "PostgreSQL is responding"

        # Check database size
        local db_size=$(sudo -u postgres psql -t -c "SELECT pg_size_pretty(pg_database_size('odoo'));" 2>/dev/null | tr -d ' ')
        log_info "Odoo database size: $db_size"

        # Check connections
        local connections=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tr -d ' ')
        log_info "Active DB connections: $connections"

        return 0
    else
        log_fail "PostgreSQL is not responding"
        return 1
    fi
}

# Check Odoo
check_odoo() {
    local odoo_url="http://127.0.0.1:8069"

    if curl -s --max-time 5 "$odoo_url/web/login" &>/dev/null; then
        log_pass "Odoo is responding on port 8069"

        # Check Odoo workers
        local worker_count=$(ps aux | grep "[o]doo-bin" | grep -c "workers" || echo "0")
        log_info "Odoo workers configured: $worker_count"

        return 0
    else
        log_fail "Odoo is not responding on port 8069"
        return 1
    fi
}

# Check Nginx
check_nginx() {
    if curl -s --max-time 5 "http://127.0.0.1:80" &>/dev/null; then
        log_pass "Nginx is responding on port 80"
        return 0
    else
        log_fail "Nginx is not responding on port 80"
        return 1
    fi
}

# Check vault sync
check_vault_sync() {
    local vault_dir="$DEPLOY_DIR/vault"

    if [ -d "$vault_dir" ]; then
        local file_count=$(find "$vault_dir" -type f 2>/dev/null | wc -l)
        log_pass "Vault directory exists ($file_count files)"

        # Check git status
        cd "$DEPLOY_DIR"
        if git status &>/dev/null; then
            local changes=$(git status --porcelain 2>/dev/null | wc -l)
            if [ "$changes" -gt 0 ]; then
                log_warn "Vault has $changes uncommitted changes"
            else
                log_pass "Vault is clean (no uncommitted changes)"
            fi
        fi

        return 0
    else
        log_fail "Vault directory not found"
        return 1
    fi
}

# Check Security Enforcer
check_security() {
    local security_dir="$DEPLOY_DIR/platinum/security"
    local audit_log="$security_dir/audit/audit_log.jsonl"

    if [ -d "$security_dir" ]; then
        log_pass "Security Enforcer directory exists"

        # Check last security scan
        if [ -f "$audit_log" ]; then
            local last_scan=$(tail -1 "$audit_log" 2>/dev/null | jq -r '.timestamp' 2>/dev/null || echo "unknown")
            log_info "Last security scan: $last_scan"
        fi

        # Check quarantine
        local quarantine_count=$(find "$security_dir/quarantine" -type f 2>/dev/null | wc -l)
        if [ "$quarantine_count" -gt 0 ]; then
            log_warn "Quarantine contains $quarantine_count file(s)"
        else
            log_pass "Quarantine is empty"
        fi

        return 0
    else
        log_warn "Security Enforcer directory not found"
        return 0
    fi
}

# Check logs
check_logs() {
    local log_dir="$LOG_DIR"

    if [ -d "$log_dir" ]; then
        local log_size=$(du -sh "$log_dir" 2>/dev/null | cut -f1)
        log_pass "Log directory size: $log_size"

        # Check for recent errors
        local error_count=$(find "$log_dir" -name "*.log" -mtime -1 -exec grep -l "ERROR\|CRITICAL" {} \; 2>/dev/null | wc -l)
        if [ "$error_count" -gt 0 ]; then
            log_warn "$error_count log file(s) contain errors from last 24h"
        else
            log_pass "No errors in logs from last 24h"
        fi

        return 0
    else
        log_warn "Log directory not found"
        return 0
    fi
}

# Check backups
check_backups() {
    local backup_dir="/var/backups/ai-employee"

    if [ -d "$backup_dir" ]; then
        local backup_count=$(find "$backup_dir" -type f -mtime -7 2>/dev/null | wc -l)
        if [ "$backup_count" -gt 0 ]; then
            log_pass "Backups exist ($backup_count files from last 7 days)"
        else
            log_warn "No backups from last 7 days"
        fi

        local backup_size=$(du -sh "$backup_dir" 2>/dev/null | cut -f1)
        log_info "Total backup size: $backup_size"

        return 0
    else
        log_warn "Backup directory not found"
        return 0
    fi
}

# Check SSH keys
check_ssh_keys() {
    local ssh_dir="/home/$DEPLOY_USER/.ssh"

    if [ -d "$ssh_dir" ]; then
        if [ -f "$ssh_dir/vault_sync_key" ]; then
            local perms=$(stat -c "%a" "$ssh_dir/vault_sync_key" 2>/dev/null)
            if [ "$perms" = "600" ]; then
                log_pass "Vault sync SSH key has correct permissions (600)"
            else
                log_warn "Vault sync SSH key has incorrect permissions ($perms, should be 600)"
            fi
        else
            log_warn "Vault sync SSH key not found"
        fi

        return 0
    else
        log_warn "SSH directory not found"
        return 0
    fi
}

# Print summary
print_summary() {
    echo ""
    echo "================================"
    echo "  Health Check Summary"
    echo "================================"
    echo ""
    echo -e "  ${GREEN}Passed:${NC}   $PASSED"
    echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
    echo -e "  ${RED}Failed:${NC}   $FAILURES"
    echo ""

    local total=$((PASSED + WARNINGS + FAILURES))
    local health_pct=$((PASSED * 100 / total))

    if [ $FAILURES -eq 0 ]; then
        echo -e "  ${GREEN}✓ Overall Status: HEALTHY (${health_pct}%)${NC}"
        return 0
    elif [ $FAILURES -lt 3 ]; then
        echo -e "  ${YELLOW}⚠ Overall Status: DEGRADED (${health_pct}%)${NC}"
        return 1
    else
        echo -e "  ${RED}✗ Overall Status: UNHEALTHY (${health_pct}%)${NC}"
        return 2
    fi
}

# Print header
print_header() {
    echo ""
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}  AI Employee Health Check${NC}"
    echo -e "${CYAN}================================${NC}"
    echo ""
    echo "  Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  Hostname: $(hostname)"
    echo "  Uptime: $(uptime -p)"
    echo ""
}

# Main
main() {
    print_header

    echo -e "${BLUE}Services:${NC}"
    check_service "ai-employee-orchestrator" "Orchestrator" || true
    check_service "ai-employee-watcher" "Watcher" || true
    check_service "ai-employee-vault-sync" "Vault Sync" || true
    check_service "ai-employee-security-enforcer" "Security Enforcer" || true
    check_service "odoo" "Odoo ERP" || true
    check_service "postgresql" "PostgreSQL" || true
    check_service "nginx" "Nginx" || true
    echo ""

    echo -e "${BLUE}System Resources:${NC}"
    check_disk "/" || true
    check_memory || true
    check_cpu || true
    echo ""

    echo -e "${BLUE}Application Health:${NC}"
    check_postgresql || true
    check_odoo || true
    check_nginx || true
    echo ""

    echo -e "${BLUE}Vault & Security:${NC}"
    check_vault_sync || true
    check_security || true
    check_ssh_keys || true
    echo ""

    echo -e "${BLUE}Maintenance:${NC}"
    check_logs || true
    check_backups || true
    echo ""

    print_summary
}

# Run main
main

exit $FAILURES
