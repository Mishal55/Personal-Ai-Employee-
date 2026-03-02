#!/bin/bash
# ============================================
# AI Employee Notification Script
# Sends alerts for deployment, health checks, and security events
# Supports: Email, Slack, Teams
# ============================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/notifications.json"
LOG_FILE="${SCRIPT_DIR}/../logs/notifications.log"

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    SLACK_WEBHOOK=$(jq -r '.slack.webhook_url // ""' "$CONFIG_FILE")
    TEAMS_WEBHOOK=$(jq -r '.teams.webhook_url // ""' "$CONFIG_FILE")
    EMAIL_RECIPIENTS=$(jq -r '.email.recipients // []' "$CONFIG_FILE")
    ENABLED_CHANNELS=$(jq -r '.enabled_channels // ["slack"]' "$CONFIG_FILE")
else
    SLACK_WEBHOOK=""
    TEAMS_WEBHOOK=""
    EMAIL_RECIPIENTS="[]"
    ENABLED_CHANNELS='["slack"]'
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

# Send Slack notification
send_slack() {
    local title="$1"
    local message="$2"
    local color="$3"

    if [ -z "$SLACK_WEBHOOK" ]; then
        log "Slack webhook not configured"
        return 1
    fi

    local payload=$(cat <<EOF
{
    "blocks": [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "$title"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "$message"
            }
        }
    ],
    "attachments": [
        {
            "color": "$color",
            "footer": "AI Employee Notifications",
            "ts": $(date +%s)
        }
    ]
}
EOF
)

    curl -s -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK" > /dev/null

    log "Slack notification sent: $title"
}

# Send Teams notification
send_teams() {
    local title="$1"
    local message="$2"
    local color="$3"

    if [ -z "$TEAMS_WEBHOOK" ]; then
        log "Teams webhook not configured"
        return 1
    fi

    local payload=$(cat <<EOF
{
    "@type": "MessageCard",
    "@context": "http://schema.org/extensions",
    "themeColor": "$color",
    "summary": "$title",
    "sections": [
        {
            "activityTitle": "$title",
            "activitySubtitle": "AI Employee Notifications",
            "text": "$message",
            "facts": [
                {
                    "name": "Timestamp",
                    "value": "$(date '+%Y-%m-%d %H:%M:%S')"
                }
            ]
        }
    ]
}
EOF
)

    curl -s -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$TEAMS_WEBHOOK" > /dev/null

    log "Teams notification sent: $title"
}

# Send email notification
send_email() {
    local subject="$1"
    local body="$2"

    if [ -z "$EMAIL_RECIPIENTS" ] || [ "$EMAIL_RECIPIENTS" = "[]" ]; then
        log "Email recipients not configured"
        return 1
    fi

    # Use mail command if available
    if command -v mail &> /dev/null; then
        echo "$body" | mail -s "$subject" $(echo "$EMAIL_RECIPIENTS" | jq -r '.[]')
        log "Email notification sent: $subject"
    else
        log "mail command not available"
        return 1
    fi
}

# Send notification to all enabled channels
send_notification() {
    local title="$1"
    local message="$2"
    local type="$3"  # info, warning, error, success

    # Set color based on type
    local color="good"
    case "$type" in
        error|critical)
            color="danger"
            ;;
        warning)
            color="warning"
            ;;
        success)
            color="good"
            ;;
        *)
            color="#0076D7"
            ;;
    esac

    # Send to enabled channels
    echo "$ENABLED_CHANNELS" | jq -r '.[]' | while read -r channel; do
        case "$channel" in
            slack)
                send_slack "$title" "$message" "$color"
                ;;
            teams)
                send_teams "$title" "$message" "$color"
                ;;
            email)
                send_email "[AI Employee] $title" "$message"
                ;;
        esac
    done
}

# Deployment notification
notify_deploy() {
    local environment="$1"
    local status="$2"
    local details="$3"

    local title="🚀 Deployment - $environment"
    local message=$(cat <<EOF
*Status:* $status
*Environment:* $environment
*Time:* $(date '+%Y-%m-%d %H:%M:%S')

*Details:*
$details
EOF
)

    local type="success"
    if [ "$status" = "failed" ]; then
        type="error"
    fi

    send_notification "$title" "$message" "$type"
}

# Health check notification
notify_health() {
    local service="$1"
    local status="$2"
    local details="$3"

    local icon="✅"
    local type="success"

    if [ "$status" = "unhealthy" ]; then
        icon="❌"
        type="error"
    elif [ "$status" = "degraded" ]; then
        icon="⚠️"
        type="warning"
    fi

    local title="$icon Health Alert: $service"
    local message=$(cat <<EOF
*Service:* $service
*Status:* $status
*Time:* $(date '+%Y-%m-%d %H:%M:%S')

*Details:*
$details
EOF
)

    send_notification "$title" "$message" "$type"
}

# Security alert notification
notify_security() {
    local alert_type="$1"
    local severity="$2"
    local details="$3"

    local icon="🔒"
    case "$severity" in
        critical)
            icon="🚨"
            ;;
        high)
            icon="⚠️"
            ;;
        medium)
            icon="🟡"
            ;;
    esac

    local title="$icon Security Alert: $alert_type"
    local message=$(cat <<EOF
*Alert Type:* $alert_type
*Severity:* $severity
*Time:* $(date '+%Y-%m-%d %H:%M:%S')

*Details:*
$details
EOF
)

    send_notification "$title" "$message" "error"
}

# Approval request notification
notify_approval_request() {
    local request_type="$1"
    local amount="$2"
    local requester="$3"
    local details="$4"

    local title="📋 Approval Request: $request_type"
    local message=$(cat <<EOF
*Request Type:* $request_type
*Amount/Count:* $amount
*Requester:* $requester
*Time:* $(date '+%Y-%m-%d %H:%M:%S')

*Details:*
$details

*Action Required:* Please review and approve/reject in the AI Employee portal.
EOF
)

    send_notification "$title" "$message" "warning"
}

# Show help
show_help() {
    cat << EOF
AI Employee Notification Script

Usage: $0 <command> [options]

Commands:
    deploy <env> <status> <details>     Send deployment notification
    health <service> <status> <details> Send health check notification
    security <type> <severity> <details> Send security alert
    approval <type> <amount> <requester> <details>
                                        Send approval request
    test                                Send test notification
    setup                               Interactive setup

Options:
    --help, -h                          Show this help

Examples:
    $0 deploy production success "All services started"
    $0 health odoo unhealthy "Service not responding"
    $0 security "Secret detected" critical ".env file found in vault"
    $0 approval Payment 500 john@example.com "Invoice payment request"

Configuration:
    Edit config/notifications.json to configure webhooks and recipients

EOF
}

# Interactive setup
setup_config() {
    echo ""
    echo "🔧 Notification Setup Wizard"
    echo ""

    mkdir -p "$(dirname "$CONFIG_FILE")"

    # Slack
    echo "📱 Slack Configuration"
    read -p "   Slack webhook URL: " slack_url

    # Teams
    echo ""
    echo "📱 Microsoft Teams Configuration"
    read -p "   Teams webhook URL: " teams_url

    # Email
    echo ""
    echo "📧 Email Configuration"
    echo "   Email recipients (comma-separated):"
    read -p "   " email_list

    # Enabled channels
    echo ""
    echo "🔄 Enabled Channels"
    echo "   1. Slack"
    echo "   2. Teams"
    echo "   3. Email"
    echo "   Select channels (comma-separated, e.g., 1,3):"
    read -p "   " channel_selection

    channels="[]"
    if [[ "$channel_selection" == *"1"* ]]; then
        channels='["slack"'
    fi
    if [[ "$channel_selection" == *"2"* ]]; then
        if [ "$channels" = "[]" ]; then
            channels='["teams"'
        else
            channels="${channels%]}, \"teams\""
        fi
    fi
    if [[ "$channel_selection" == *"3"* ]]; then
        if [ "$channels" = "[]" ]; then
            channels='["email"'
        else
            channels="${channels%]}, \"email\""
        fi
    fi
    if [ "$channels" != "[]" ]; then
        channels="$channels]"
    fi

    # Create config
    cat > "$CONFIG_FILE" << EOF
{
    "slack": {
        "webhook_url": "$slack_url"
    },
    "teams": {
        "webhook_url": "$teams_url"
    },
    "email": {
        "recipients": [$(echo "$email_list" | sed 's/,/","/g' | sed 's/^/"/' | sed 's/$/"/')]
    },
    "enabled_channels": $channels
}
EOF

    echo ""
    echo "✅ Configuration saved to $CONFIG_FILE"
}

# Send test notification
send_test() {
    send_notification \
        "🧪 Test Notification" \
        "This is a test notification from AI Employee." \
        "info"
}

# Main
case "${1:-help}" in
    deploy)
        notify_deploy "$2" "$3" "$4"
        ;;
    health)
        notify_health "$2" "$3" "$4"
        ;;
    security)
        notify_security "$2" "$3" "$4"
        ;;
    approval)
        notify_approval_request "$2" "$3" "$4" "$5"
        ;;
    test)
        send_test
        ;;
    setup)
        setup_config
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
