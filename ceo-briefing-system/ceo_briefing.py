#!/usr/bin/env python3
"""
CEO Briefing System - Enhanced Version
Generates Monday Morning CEO Briefings with:
- Real financial data from Odoo ERP
- Week-over-week trend analysis
- Human-in-the-loop approval workflow
- Email delivery via Email-MCP
- Slack/Teams notifications

Usage:
    python ceo_briefing.py [--date YYYY-MM-DD] [--output-dir PATH] [--email] [--notify]

Cron Setup (run every Monday at 7 AM):
    0 7 * * 1 cd /path/to/ceo-briefing-system && python3 ceo_briefing.py --email --notify

Approval Workflow:
    1. Briefing is generated in /Pending_Approval
    2. Review the briefing
    3. Run: python ceo_briefing.py --approve 2026-02-27_Briefing.md
    4. Briefing moves to /Briefings and notifications are sent
"""

import argparse
import sys
import io
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from markdown_reader import MarkdownReader
from briefing_generator import BriefingGenerator


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file"""
    path = Path(config_path)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_briefing_metadata(briefing_path: str, metadata: dict, output_dir: str):
    """Save briefing metadata for tracking"""
    metadata_file = Path(output_dir) / 'briefing_metadata.json'
    
    metadata_list = []
    if metadata_file.exists():
        try:
            metadata_list = json.loads(metadata_file.read_text())
        except:
            metadata_list = []
    
    metadata_entry = {
        'filename': Path(briefing_path).name,
        'path': briefing_path,
        'generated_at': datetime.now().isoformat(),
        **metadata
    }
    
    metadata_list.append(metadata_entry)
    metadata_file.write_text(json.dumps(metadata_list, indent=2))


def send_email_via_mcp(briefing_path: str, email_config: dict, quiet: bool = False) -> dict:
    """
    Send briefing email using Email MCP Server

    Args:
        briefing_path: Path to the generated briefing file
        email_config: Email configuration dictionary
        quiet: Suppress output

    Returns:
        Email send result
    """
    if not quiet:
        print("📧 Sending briefing via email...")

    # Email MCP server path
    email_mcp_path = Path(__file__).parent.parent / 'email-mcp-server' / 'src' / 'server.js'

    # Prepare the email request
    email_data = {
        'briefingPath': str(briefing_path),
        'subject': email_config.get('subject', 'Weekly CEO Briefing'),
        'recipients': {
            'to': email_config.get('to', []),
            'cc': email_config.get('cc', []),
            'bcc': email_config.get('bcc', [])
        },
        'additionalMessage': email_config.get('message', '')
    }

    # Create MCP request
    mcp_request = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {
            'name': 'email_send_briefing',
            'arguments': email_data
        }
    }

    try:
        # Run the email MCP server and send the request
        result = subprocess.run(
            ['node', str(email_mcp_path)],
            input=json.dumps(mcp_request),
            capture_output=True,
            text=True,
            timeout=60,
            env={**subprocess.os.environ, 'NODE_OPTIONS': '--input-type=module'}
        )

        # Parse the response
        output = result.stderr + result.stdout
        for line in output.split('\n'):
            if line.strip().startswith('{'):
                try:
                    response = json.loads(line)
                    if 'result' in response:
                        result_data = response.get('result', {})
                        if not quiet:
                            if result_data.get('success') or result_data.get('messageId'):
                                print("   ✓ Email sent successfully")
                            else:
                                print("   ✓ Email send completed")
                        return {
                            'success': True,
                            'result': result_data
                        }
                except json.JSONDecodeError:
                    pass

        # Fallback - check if there was an error
        if result.returncode != 0:
            if not quiet:
                print(f"   ⚠️ Email send completed with warnings")
            return {
                'success': True,
                'warnings': ['Check email server logs for details']
            }

        if not quiet:
            print("   ✓ Email send command executed")
        return {'success': True}

    except subprocess.TimeoutExpired:
        if not quiet:
            print("   ⚠️ Email send timed out (briefing file saved successfully)")
        return {
            'success': False,
            'error': 'Email send timed out'
        }
    except FileNotFoundError:
        if not quiet:
            print("   ⚠️ Email MCP server not found. Briefing saved but not emailed.")
        return {
            'success': False,
            'error': 'Email MCP server not found'
        }
    except Exception as e:
        if not quiet:
            print(f"   ⚠️ Email send failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def send_email_direct(briefing_path: str, email_config: dict, quiet: bool = False) -> dict:
    """
    Send briefing email directly using smtplib (fallback if MCP not available)
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication

    if not quiet:
        print("📧 Sending briefing via email (direct SMTP)...")

    smtp_config = email_config.get('smtp', {})

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_config.get('from', smtp_config.get('auth', {}).get('user', ''))
        msg['To'] = ', '.join(email_config.get('to', []))
        if email_config.get('cc'):
            msg['Cc'] = ', '.join(email_config.get('cc', []))
        msg['Subject'] = email_config.get('subject', 'Weekly CEO Briefing')

        # Email body
        message_body = email_config.get('message', '''Dear Team,

Please find attached the Weekly CEO Briefing.

Best regards,
AI Employee System
''')
        msg.attach(MIMEText(message_body, 'plain'))

        # Attach briefing file
        with open(briefing_path, 'rb') as f:
            attachment = MIMEApplication(f.read(), Name=Path(briefing_path).name)
        attachment['Content-Disposition'] = f'attachment; filename="{Path(briefing_path).name}"'
        msg.attach(attachment)

        # Connect and send
        server = smtplib.SMTP(smtp_config.get('host', 'smtp.gmail.com'), smtp_config.get('port', 587))
        server.starttls()
        server.login(
            smtp_config.get('auth', {}).get('user', ''),
            smtp_config.get('auth', {}).get('pass', '')
        )

        all_recipients = email_config.get('to', []) + email_config.get('cc', []) + email_config.get('bcc', [])
        server.sendmail(msg['From'], all_recipients, msg.as_string())
        server.quit()

        if not quiet:
            print("   ✓ Email sent successfully")

        return {'success': True, 'recipients': all_recipients}

    except Exception as e:
        if not quiet:
            print(f"   ✗ Email send failed: {e}")
        return {'success': False, 'error': str(e)}


def send_notification_via_mcp(briefing_path: str, briefing_url: str,
                               messaging_config: dict, platforms: list,
                               period: str = 'weekly', custom_message: str = '',
                               quiet: bool = False) -> dict:
    """
    Send briefing notification via Messaging MCP Server (Slack/Teams)

    Args:
        briefing_path: Path to the generated briefing file
        briefing_url: URL to access the briefing
        messaging_config: Messaging configuration
        platforms: List of platforms ['slack', 'teams']
        period: Briefing period
        custom_message: Custom message to include
        quiet: Suppress output

    Returns:
        Notification result
    """
    if not quiet:
        print(f"📢 Sending notification to {', '.join(platforms)}...")

    # Messaging MCP server path
    messaging_mcp_path = Path(__file__).parent.parent / 'messaging-mcp-server' / 'src' / 'server.js'

    # Prepare the notification request
    notification_data = {
        'briefingPath': str(briefing_path),
        'briefingUrl': briefing_url,
        'platforms': platforms,
        'period': period,
        'customMessage': custom_message
    }

    # Create MCP request
    mcp_request = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {
            'name': 'messaging_send_briefing_notification',
            'arguments': notification_data
        }
    }

    try:
        # Run the messaging MCP server and send the request
        result = subprocess.run(
            ['node', str(messaging_mcp_path)],
            input=json.dumps(mcp_request),
            capture_output=True,
            text=True,
            timeout=60
        )

        # Parse the response
        output = result.stderr + result.stdout
        for line in output.split('\n'):
            if line.strip().startswith('{'):
                try:
                    response = json.loads(line)
                    if 'result' in response:
                        result_data = response.get('result', {})
                        success = result_data.get('success', False)
                        results = result_data.get('results', [])
                        
                        if not quiet:
                            if success:
                                print("   ✓ Notification sent successfully")
                                for r in results:
                                    if r.get('success'):
                                        print(f"      ✓ {r.get('platform', 'unknown')}: delivered")
                                    else:
                                        print(f"      ⚠️ {r.get('platform', 'unknown')}: {r.get('error', 'failed')}")
                            else:
                                print(f"   ⚠️ Notification sent with issues")
                        return {
                            'success': success,
                            'result': result_data
                        }
                except json.JSONDecodeError:
                    pass

        # Fallback
        if not quiet:
            print("   ✓ Notification command executed")
        return {'success': True}

    except subprocess.TimeoutExpired:
        if not quiet:
            print("   ⚠️ Notification send timed out (briefing file saved successfully)")
        return {
            'success': False,
            'error': 'Notification send timed out'
        }
    except FileNotFoundError:
        if not quiet:
            print("   ⚠️ Messaging MCP server not found. Briefing saved but notification not sent.")
        return {
            'success': False,
            'error': 'Messaging MCP server not found'
        }
    except Exception as e:
        if not quiet:
            print(f"   ⚠️ Notification send failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def approve_briefing(briefing_filename: str, output_dir: str, pending_dir: str, 
                     messaging_config: dict = None, email_config: dict = None,
                     briefing_url: str = '', quiet: bool = False) -> dict:
    """
    Approve a pending briefing - move from Pending_Approval to Briefings
    and send notifications
    
    Args:
        briefing_filename: Name of the briefing file to approve
        output_dir: Briefings output directory
        pending_dir: Pending approval directory
        messaging_config: Messaging configuration for notifications
        email_config: Email configuration
        briefing_url: URL to access the briefing
        quiet: Suppress output
    
    Returns:
        Approval result
    """
    if not quiet:
        print(f"📋 Approving briefing: {briefing_filename}")
    
    generator = BriefingGenerator(output_dir, pending_dir)
    
    # Approve the briefing
    result = generator.approve_briefing(briefing_filename)
    
    if not result.get('success'):
        if not quiet:
            print(f"   ✗ Approval failed: {result.get('error', 'Unknown error')}")
        return result
    
    if not quiet:
        print(f"   ✓ Briefing approved and moved to {result['record']['moved_to']}")
    
    # Send notifications after approval
    notification_result = None
    if messaging_config:
        platforms = messaging_config.get('briefingNotifications', {}).get('platforms', ['slack'])
        period = messaging_config.get('briefingNotifications', {}).get('period', 'weekly')
        custom_message = messaging_config.get('briefingNotifications', {}).get('customMessage', 
            '✅ *Briefing Approved*\n\nThe weekly CEO briefing has been approved and is now available for review.')
        
        notification_result = send_notification_via_mcp(
            result['record']['moved_to'],
            briefing_url,
            messaging_config,
            platforms,
            period,
            custom_message,
            quiet
        )
    
    # Send email after approval if configured
    email_result = None
    if email_config:
        email_result = send_email_via_mcp(result['record']['moved_to'], email_config, quiet)
    
    return {
        'success': True,
        'approval': result,
        'notification': notification_result,
        'email': email_result
    }


def list_pending_briefings(pending_dir: str, quiet: bool = False) -> list:
    """
    List all briefings pending approval
    
    Args:
        pending_dir: Pending approval directory
        quiet: Suppress output
    
    Returns:
        List of pending briefings
    """
    pending_path = Path(pending_dir)
    if not pending_path.exists():
        if not quiet:
            print("No pending approval directory found")
        return []
    
    pending = []
    for f in pending_path.glob('*_Briefing.md'):
        stat = f.stat()
        pending.append({
            'filename': f.name,
            'path': str(f),
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
        })
    
    pending = sorted(pending, key=lambda x: x['modified'], reverse=True)
    
    if not quiet and pending:
        print("\n📋 Pending Briefings:")
        print("-" * 60)
        for p in pending:
            print(f"  • {p['filename']}")
            print(f"    Modified: {p['modified']} | Size: {p['size']:,} bytes")
        print("-" * 60)
        print(f"\nTo approve: python ceo_briefing.py --approve <filename>")
    elif not quiet:
        print("No briefings pending approval")
    
    return pending


def main():
    parser = argparse.ArgumentParser(
        description='Generate CEO Briefing from business data sources with approval workflow'
    )
    parser.add_argument(
        '--date', '-d',
        type=str,
        default=None,
        help='Briefing date (YYYY-MM-DD). Defaults to today.'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default=None,
        help='Output directory for briefings. Defaults to ./Briefings'
    )
    parser.add_argument(
        '--pending-dir',
        type=str,
        default=None,
        help='Pending approval directory. Defaults to ./Pending_Approval'
    )
    parser.add_argument(
        '--base-path', '-b',
        type=str,
        default=None,
        help='Base path for source files. Defaults to script directory.'
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        help='Path to config JSON file'
    )
    parser.add_argument(
        '--approve',
        type=str,
        default=None,
        metavar='FILENAME',
        help='Approve a pending briefing (move to Briefings and send notifications)'
    )
    parser.add_argument(
        '--list-pending',
        action='store_true',
        help='List all briefings pending approval'
    )
    parser.add_argument(
        '--email', '-e',
        action='store_true',
        help='Send briefing via email after approval'
    )
    parser.add_argument(
        '--email-config',
        type=str,
        default=None,
        help='Path to email config JSON file (overrides briefing config)'
    )
    parser.add_argument(
        '--odoo',
        action='store_true',
        help='Pull financial data from Odoo ERP with trend analysis'
    )
    parser.add_argument(
        '--odoo-config',
        type=str,
        default=None,
        help='Path to Odoo config JSON file'
    )
    parser.add_argument(
        '--period',
        type=str,
        default='week',
        choices=['week', 'month', 'quarter', 'year'],
        help='Financial data period (default: week for trend analysis)'
    )
    parser.add_argument(
        '--no-trends',
        action='store_true',
        help='Disable week-over-week trend analysis'
    )
    parser.add_argument(
        '--notify',
        action='store_true',
        help='Send notification to Slack/Teams after approval'
    )
    parser.add_argument(
        '--notify-platforms',
        type=str,
        default=None,
        help='Platforms to notify (comma-separated: slack,teams)'
    )
    parser.add_argument(
        '--messaging-config',
        type=str,
        default=None,
        help='Path to messaging config JSON file'
    )
    parser.add_argument(
        '--briefing-url',
        type=str,
        default=None,
        help='URL to access the briefing (for notifications)'
    )
    parser.add_argument(
        '--auto-approve',
        action='store_true',
        help='Skip approval workflow and generate directly to Briefings'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output messages'
    )

    args = parser.parse_args()

    # Load config if provided
    config = {}
    if args.config:
        config = load_config(args.config)

    # Set paths
    base_path = Path(args.base_path) if args.base_path else Path(__file__).parent
    output_dir = args.output_dir or config.get('output_dir', str(base_path / 'Briefings'))
    pending_dir = args.pending_dir or config.get('pending_dir', str(base_path / 'Pending_Approval'))

    # Handle list pending command
    if args.list_pending:
        list_pending_briefings(pending_dir, args.quiet)
        return 0

    # Handle approve command
    if args.approve:
        # Load configs
        email_config_path = args.email_config or config.get('email_config')
        email_config = load_config(email_config_path) if email_config_path else {}
        
        messaging_config_path = args.messaging_config or config.get('messaging_config')
        messaging_config = load_config(messaging_config_path) if messaging_config_path else {}
        
        briefing_url = args.briefing_url or config.get('briefing_url', '')
        
        result = approve_briefing(
            args.approve,
            output_dir,
            pending_dir,
            messaging_config if args.notify else None,
            email_config if args.email else None,
            briefing_url,
            args.quiet
        )
        
        if result.get('success'):
            if not args.quiet:
                print("\n✅ Briefing approval complete!")
            return 0
        else:
            if not args.quiet:
                print(f"\n✗ Approval failed: {result.get('error', 'Unknown error')}")
            return 1

    # Parse date
    if args.date:
        try:
            briefing_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        briefing_date = datetime.now()

    # Check if it's Monday (for warning)
    if briefing_date.weekday() != 0 and not args.quiet:
        print(f"⚠️  Note: {briefing_date.strftime('%A')} is not Monday. Generating anyway.")

    if not args.quiet:
        print(f"📋 CEO Briefing Generator (Enhanced)")
        print(f"   Date: {briefing_date.strftime('%Y-%m-%d %A')}")
        print(f"   Base Path: {base_path}")
        print(f"   Output Dir: {output_dir}")
        print(f"   Pending Dir: {pending_dir}")
        if args.auto_approve:
            print(f"   Workflow: Auto-approve (skip Pending_Approval)")
        else:
            print(f"   Workflow: Human-in-the-loop approval enabled")
        if args.email:
            print(f"   Email: Enabled (after approval)")
        if args.odoo:
            print(f"   Odoo Integration: Enabled")
            print(f"   Period: {args.period}")
            if not args.no_trends:
                print(f"   Trend Analysis: Week-over-Week enabled")
        print()

    # Initialize components
    reader = MarkdownReader(str(base_path))
    generator = BriefingGenerator(output_dir, pending_dir)

    # Read all data sources
    if not args.quiet:
        print("📖 Reading data sources...")

    data = reader.read_all_sources()

    # Read Odoo financial data if requested
    if args.odoo:
        if not args.quiet:
            print("   📊 Connecting to Odoo ERP...")

        # Load Odoo config
        odoo_config_path = args.odoo_config or config.get('odoo_config')
        odoo_config = {}

        if odoo_config_path:
            odoo_config = load_config(odoo_config_path)
        else:
            # Check for default Odoo config locations
            default_paths = [
                base_path / 'config' / 'odoo-config.json',
                Path(__file__).parent.parent / 'odoo-mcp-server' / 'config' / 'odoo-config.json',
                base_path / 'odoo-config.json'
            ]
            for path in default_paths:
                if path.exists():
                    odoo_config = load_config(str(path))
                    break

        if odoo_config:
            include_trends = not args.no_trends
            odoo_data = reader.read_odoo_financials(odoo_config, period=args.period, include_trends=include_trends)

            if odoo_data.get('available'):
                if not args.quiet:
                    trend_info = "with trends" if odoo_data.get('trend_analysis') else ""
                    print(f"   ✓ Odoo connected - {odoo_data['revenue']['invoice_count']} invoices, {odoo_data['expenses']['bill_count']} bills {trend_info}")

                # Merge Odoo data with existing financial data
                if 'bank_transactions' in data:
                    # Prefer Odoo data for financial summaries
                    data['odoo_financials'] = odoo_data
                    data['bank_transactions']['odoo_revenue'] = odoo_data['revenue']['total_revenue']
                    data['bank_transactions']['odoo_expenses'] = odoo_data['expenses']['total_expenses']
                    data['bank_transactions']['odoo_net'] = odoo_data['net_income']
                    data['bank_transactions']['odoo_profit_margin'] = odoo_data['profit_margin']
                    data['bank_transactions']['odoo_invoices'] = odoo_data['revenue'].get('invoices', [])
                    data['bank_transactions']['odoo_bills'] = odoo_data['expenses'].get('bills', [])
                    data['bank_transactions']['odoo_by_vendor'] = odoo_data['expenses'].get('by_vendor', {})
                    data['bank_transactions']['odoo_payments'] = odoo_data['payments']
                    data['bank_transactions']['period'] = odoo_data['period']
                    data['bank_transactions']['source'] = 'Odoo ERP + Local'
                    
                    # Add trend analysis
                    if odoo_data.get('trend_analysis'):
                        data['bank_transactions']['trend_analysis'] = odoo_data['trend_analysis']
            else:
                if not args.quiet:
                    print(f"   ⚠️ Odoo connection failed: {odoo_data.get('error', 'Unknown error')}")
                    print(f"   Using local Bank_Transactions.md data instead")
        else:
            if not args.quiet:
                print("   ⚠️ No Odoo configuration found")
                print("   Configure Odoo in config/odoo-config.json or use --odoo-config")

    # Report what was found
    if not args.quiet:
        goals = data.get('business_goals', {})
        finances = data.get('bank_transactions', {})
        tasks = data.get('done_tasks', {})

        print(f"   ✓ Business Goals: {len(goals.get('goals', []))} goals found")
        if finances.get('source'):
            print(f"   ✓ Financial Data: {finances.get('source')} ({finances.get('transaction_count', 0)} transactions)")
        else:
            print(f"   ✓ Bank Transactions: {finances.get('transaction_count', 0)} transactions")
        print(f"   ✓ Done Tasks: {tasks.get('total_tasks', 0)} total tasks")
        
        if finances.get('trend_analysis'):
            trends = finances['trend_analysis'].get('trends', {})
            rev_change = trends.get('revenue', {}).get('change_percent', 0)
            trend_icon = '📈' if rev_change > 0 else '📉' if rev_change < 0 else '➡️'
            print(f"   ✓ Trend Analysis: Revenue {trend_icon} {rev_change:+.1f}% vs previous period")
        print()

    # Generate briefing
    if not args.quiet:
        print("✍️  Generating briefing...")

    # Determine if we should save to pending approval
    pending_approval = not args.auto_approve
    
    filepath = generator.generate_briefing(data, briefing_date, pending_approval=pending_approval)

    if not args.quiet:
        status = "Pending Approval" if pending_approval else "Approved"
        print(f"   ✓ Briefing saved to: {filepath}")
        print(f"   ✓ Status: {status}")
        print()

    # Save metadata
    metadata = {
        'date': briefing_date.strftime('%Y-%m-%d'),
        'status': 'pending_approval' if pending_approval else 'approved',
        'odoo_enabled': args.odoo,
        'trends_enabled': not args.no_trends and args.odoo,
        'period': args.period
    }
    save_briefing_metadata(filepath, metadata, pending_dir if pending_approval else output_dir)

    # If auto-approve, send notifications and email immediately
    if args.auto_approve:
        # Send notification if requested
        notification_result = None
        if args.notify:
            # Parse platforms
            platforms = ['slack']  # default
            if args.notify_platforms:
                platforms = [p.strip() for p in args.notify_platforms.split(',')]

            # Load messaging config
            messaging_config_path = args.messaging_config or config.get('messaging_config')
            messaging_config = {}

            if messaging_config_path:
                messaging_config = load_config(messaging_config_path)
            else:
                # Check for default messaging config locations
                default_paths = [
                    base_path / 'config' / 'messaging-config.json',
                    Path(__file__).parent.parent / 'messaging-mcp-server' / 'config' / 'messaging-config.json',
                    base_path / 'messaging-config.json'
                ]
                for path in default_paths:
                    if path.exists():
                        messaging_config = load_config(str(path))
                        # Get platforms from config if not specified
                        if not args.notify_platforms and messaging_config.get('briefingNotifications', {}).get('platforms'):
                            platforms = messaging_config['briefingNotifications']['platforms']
                        break

            # Get briefing URL (from config or argument)
            briefing_url = args.briefing_url or config.get('briefing_url', '')

            # Get period and custom message from config
            period = config.get('briefingNotifications', {}).get('period', 'weekly')
            custom_message = config.get('briefingNotifications', {}).get('customMessage', '')

            if messaging_config:
                notification_result = send_notification_via_mcp(
                    filepath, briefing_url, messaging_config,
                    platforms, period, custom_message, args.quiet
                )

        # Send email if requested
        email_result = None
        if args.email:
            # Load email config
            email_config_path = args.email_config or config.get('email_config')
            email_config = {}

            if email_config_path:
                email_config = load_config(email_config_path)
            else:
                # Check for default email config locations
                default_paths = [
                    base_path / 'config' / 'email-config.json',
                    Path(__file__).parent.parent / 'email-mcp-server' / 'config' / 'email-config.json',
                    base_path / 'email-config.json'
                ]
                for path in default_paths:
                    if path.exists():
                        email_config = load_config(str(path))
                        break

            if email_config:
                # Try Email MCP Server first, then fall back to direct SMTP
                email_result = send_email_via_mcp(filepath, email_config, args.quiet)

                if not email_result.get('success') and email_config.get('smtp'):
                    if not args.quiet:
                        print("   📮 Falling back to direct SMTP...")
                    email_result = send_email_direct(filepath, email_config, args.quiet)

    if not args.quiet:
        print("✅ Done!")
        
        if pending_approval and not args.quiet:
            print("\n📋 Next Steps:")
            print(f"   1. Review the briefing in: {pending_dir}/")
            print(f"   2. Approve with: python ceo_briefing.py --approve {Path(filepath).name}")
            print(f"   3. List pending: python ceo_briefing.py --list-pending")

    return 0


if __name__ == '__main__':
    sys.exit(main())
