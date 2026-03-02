#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Odoo Community Accounting MCP Server - Gold Tier Feature

Provides integration with Odoo Community Edition for accounting operations.
Supports invoices, payments, customers, vendors, and financial reports.

Configuration:
    Set environment variables:
    - ODOO_URL: Odoo server URL (e.g., http://localhost:8069)
    - ODOO_DB: Database name
    - ODOO_USERNAME: Username or email
    - ODOO_PASSWORD: Password or API key
    - ODOO_COMPANY_ID: Company ID (optional, defaults to 1)

Usage:
    python odoo_accounting_mcp.py  # Run as stdio MCP server
    
Tools:
    - create_invoice: Create a new customer invoice
    - list_invoices: List invoices with filters
    - validate_invoice: Validate a draft invoice
    - register_payment: Register a payment for an invoice
    - list_customers: List all customers
    - list_vendors: List all vendors
    - get_account_report: Get financial reports (P&L, Balance Sheet)
    - reconcile_accounts: Reconcile bank statements
    - create_journal_entry: Create manual journal entries
"""

import argparse
import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


# Configuration
VAULT_PATH = Path(os.environ.get('AI_VAULT_PATH', r'D:\Personal Ai Employee\AI_Employee_Vault'))
ODOO_STATE_FILE = VAULT_PATH / 'Accounting' / 'Odoo' / 'state.json'
ODOO_LOG_FILE = VAULT_PATH / 'Logs' / 'odoo_mcp.log'

ODOO_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
ODOO_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Odoo connection settings from environment
ODOO_CONFIG = {
    'url': os.environ.get('ODOO_URL', 'http://localhost:8069'),
    'db': os.environ.get('ODOO_DB', 'odoo'),
    'username': os.environ.get('ODOO_USERNAME', 'admin'),
    'password': os.environ.get('ODOO_PASSWORD', 'admin'),
    'company_id': int(os.environ.get('ODOO_COMPANY_ID', '1'))
}


def log_message(message: str, level: str = "INFO"):
    """Log a message to the log file."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    with open(ODOO_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)


class OdooClient:
    """Client for Odoo JSON-RPC API."""
    
    def __init__(self, config: dict):
        self.config = config
        self.uid = None
        self.session = requests.Session()
        
    def authenticate(self) -> bool:
        """Authenticate with Odoo and get user ID."""
        url = f"{self.config['url']}/web/session/authenticate"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": self.config['db'],
                "login": self.config['username'],
                "password": self.config['password']
            },
            "id": 1
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            result = response.json()
            
            if result.get('result', {}).get('uid'):
                self.uid = result['result']['uid']
                log_message(f"Authenticated as user {self.uid}")
                return True
            else:
                log_message("Authentication failed", "ERROR")
                return False
                
        except Exception as e:
            log_message(f"Authentication error: {e}", "ERROR")
            return False
    
    def execute_kw(self, model: str, method: str, args: list = None, kwargs: dict = None) -> Any:
        """Execute a method on an Odoo model."""
        if not self.uid:
            if not self.authenticate():
                raise Exception("Not authenticated")
        
        url = f"{self.config['url']}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args or [],
                "kwargs": kwargs or {}
            },
            "id": 1
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            result = response.json()
            
            if 'error' in result:
                error = result['error']
                raise Exception(f"Odoo error: {error.get('message', 'Unknown error')}")
            
            return result.get('result', {})
            
        except Exception as e:
            log_message(f"Execute error on {model}.{method}: {e}", "ERROR")
            raise


# ============================================================================
# Odoo Accounting Operations
# ============================================================================

def create_invoice(partner_name: str, partner_email: str, lines: list,
                   invoice_date: Optional[str] = None,
                   payment_terms: Optional[str] = None) -> dict:
    """
    Create a new customer invoice.
    
    Args:
        partner_name: Customer name
        partner_email: Customer email
        lines: List of invoice lines with name, quantity, price
        invoice_date: Invoice date (YYYY-MM-DD)
        payment_terms: Payment terms reference
    
    Returns:
        Invoice ID and details
    """
    client = OdooClient(ODOO_CONFIG)
    
    try:
        # Find or create partner
        partner_id = client.execute_kw('res.partner', 'search', [[
            ['email', '=', partner_email]
        ]])
        
        if not partner_id:
            # Create new partner
            partner_id = client.execute_kw('res.partner', 'create', [{
                'name': partner_name,
                'email': partner_email,
                'customer_rank': 1
            }])
            log_message(f"Created new partner: {partner_name} (ID: {partner_id})")
        else:
            partner_id = partner_id[0]
        
        # Prepare invoice lines
        invoice_lines = []
        for line in lines:
            invoice_lines.append((0, 0, {
                'name': line.get('name', 'Service'),
                'quantity': line.get('quantity', 1),
                'price_unit': line.get('price', 0),
                'account_id': False  # Will use default income account
            }))
        
        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'invoice_date': invoice_date or datetime.now().strftime('%Y-%m-%d'),
            'invoice_line_ids': invoice_lines,
            'company_id': ODOO_CONFIG['company_id']
        }
        
        if payment_terms:
            invoice_vals['invoice_payment_term_id'] = payment_terms
        
        invoice_id = client.execute_kw('account.move', 'create', [invoice_vals])
        
        log_message(f"Created invoice {invoice_id} for {partner_name}")
        
        return {
            'invoice_id': invoice_id,
            'partner': partner_name,
            'partner_id': partner_id,
            'status': 'draft',
            'message': f"Invoice created successfully. ID: {invoice_id}"
        }
        
    except Exception as e:
        return {'error': str(e)}


def list_invoices(status: Optional[str] = None,
                  partner: Optional[str] = None,
                  limit: int = 20) -> dict:
    """
    List invoices with optional filters.
    
    Args:
        status: Filter by status (draft, posted, cancel)
        partner: Filter by partner name
        limit: Maximum number of results
    
    Returns:
        List of invoices
    """
    client = OdooClient(ODOO_CONFIG)
    
    try:
        domain = [['company_id', '=', ODOO_CONFIG['company_id']]]
        
        if status:
            state_map = {
                'draft': 'draft',
                'posted': 'posted',
                'cancel': 'cancel'
            }
            domain.append(['state', '=', state_map.get(status, 'draft')])
        
        if partner:
            domain.append(['partner_id', 'ilike', partner])
        
        invoices = client.execute_kw('account.move', 'search_read', [
            domain,
            ['name', 'partner_id', 'invoice_date', 'amount_total', 'amount_due', 'state']
        ], {'limit': limit, 'order': 'invoice_date desc'})
        
        # Format results
        formatted = []
        for inv in invoices:
            partner_name = inv.get('partner_id', [False, 'Unknown'])[1] if inv.get('partner_id') else 'Unknown'
            formatted.append({
                'id': inv['id'],
                'number': inv.get('name', 'N/A'),
                'partner': partner_name,
                'date': inv.get('invoice_date', 'N/A'),
                'total': inv.get('amount_total', 0),
                'due': inv.get('amount_due', 0),
                'status': inv.get('state', 'draft')
            })
        
        return {'invoices': formatted, 'count': len(formatted)}
        
    except Exception as e:
        return {'error': str(e)}


def validate_invoice(invoice_id: int) -> dict:
    """Validate (post) a draft invoice."""
    client = OdooClient(ODOO_CONFIG)
    
    try:
        client.execute_kw('account.move', 'action_post', [[invoice_id]])
        log_message(f"Validated invoice {invoice_id}")
        return {'invoice_id': invoice_id, 'status': 'posted', 'message': 'Invoice validated'}
    except Exception as e:
        return {'error': str(e)}


def register_payment(invoice_id: int, amount: float,
                     payment_date: Optional[str] = None,
                     payment_reference: Optional[str] = None) -> dict:
    """Register a payment for an invoice."""
    client = OdooClient(ODOO_CONFIG)
    
    try:
        # Get invoice data
        invoices = client.execute_kw('account.move', 'search_read', [
            [['id', '=', invoice_id]],
            ['amount_residual', 'currency_id']
        ])
        
        if not invoices:
            return {'error': f'Invoice {invoice_id} not found'}
        
        invoice = invoices[0]
        residual = invoice.get('amount_residual', 0)
        
        if amount > residual:
            return {'error': f'Payment amount ({amount}) exceeds due amount ({residual})'}
        
        # Create payment
        payment_vals = {
            'move_id': invoice_id,
            'amount': amount,
            'payment_date': payment_date or datetime.now().strftime('%Y-%m-%d'),
            'payment_reference': payment_reference or 'Payment',
            'payment_type': 'inbound'
        }
        
        # Use account.payment.register wizard
        register_id = client.execute_kw('account.payment.register', 'create', [{
            'move_ids': [(6, 0, [invoice_id])],
            'amount': amount,
            'payment_date': payment_vals['payment_date']
        }])
        
        client.execute_kw('account.payment.register', 'action_create_payments', [[register_id]])
        
        log_message(f"Registered payment of {amount} for invoice {invoice_id}")
        
        return {
            'invoice_id': invoice_id,
            'amount': amount,
            'status': 'paid' if amount >= residual else 'partial',
            'message': 'Payment registered successfully'
        }
        
    except Exception as e:
        return {'error': str(e)}


def list_customers(limit: int = 50) -> dict:
    """List all customers."""
    client = OdooClient(ODOO_CONFIG)
    
    try:
        customers = client.execute_kw('res.partner', 'search_read', [
            [['customer_rank', '>', 0]],
            ['name', 'email', 'phone', 'street', 'city', 'country_id']
        ], {'limit': limit})
        
        formatted = []
        for cust in customers:
            country = cust.get('country_id', [False, ''])[1] if cust.get('country_id') else ''
            formatted.append({
                'id': cust['id'],
                'name': cust.get('name', 'Unknown'),
                'email': cust.get('email', ''),
                'phone': cust.get('phone', ''),
                'city': cust.get('city', ''),
                'country': country
            })
        
        return {'customers': formatted, 'count': len(formatted)}
        
    except Exception as e:
        return {'error': str(e)}


def list_vendors(limit: int = 50) -> dict:
    """List all vendors."""
    client = OdooClient(ODOO_CONFIG)
    
    try:
        vendors = client.execute_kw('res.partner', 'search_read', [
            [['supplier_rank', '>', 0]],
            ['name', 'email', 'phone', 'street', 'city', 'country_id']
        ], {'limit': limit})
        
        formatted = []
        for vend in vendors:
            country = vend.get('country_id', [False, ''])[1] if vend.get('country_id') else ''
            formatted.append({
                'id': vend['id'],
                'name': vend.get('name', 'Unknown'),
                'email': vend.get('email', ''),
                'phone': vend.get('phone', ''),
                'city': vend.get('city', ''),
                'country': country
            })
        
        return {'vendors': formatted, 'count': len(formatted)}
        
    except Exception as e:
        return {'error': str(e)}


def get_account_report(report_type: str = 'profit_loss',
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None) -> dict:
    """
    Get financial reports.
    
    Args:
        report_type: 'profit_loss', 'balance_sheet', 'trial_balance'
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
    
    Returns:
        Report data
    """
    client = OdooClient(ODOO_CONFIG)
    
    try:
        # For simplicity, we'll get account moves and calculate
        domain = [
            ['company_id', '=', ODOO_CONFIG['company_id']],
            ['state', '=', 'posted']
        ]
        
        if date_from:
            domain.append(['date', '>=', date_from])
        if date_to:
            domain.append(['date', '<=', date_to])
        
        moves = client.execute_kw('account.move', 'search_read', [
            domain,
            ['name', 'date', 'amount_total', 'move_type']
        ])
        
        # Calculate totals
        revenue = sum(m.get('amount_total', 0) for m in moves if m.get('move_type') in ['out_invoice', 'out_refund'])
        expenses = sum(m.get('amount_total', 0) for m in moves if m.get('move_type') in ['in_invoice', 'in_refund'])
        
        report = {
            'report_type': report_type,
            'period': f"{date_from or 'N/A'} to {date_to or 'N/A'}",
            'revenue': revenue,
            'expenses': expenses,
            'net_income': revenue - expenses,
            'transaction_count': len(moves)
        }
        
        return report
        
    except Exception as e:
        return {'error': str(e)}


def create_journal_entry(date: str, lines: list,
                         reference: str = '') -> dict:
    """
    Create a manual journal entry.
    
    Args:
        date: Entry date (YYYY-MM-DD)
        lines: List of debit/credit lines with account_id, debit, credit, name
        reference: Reference/description
    
    Returns:
        Journal entry ID
    """
    client = OdooClient(ODOO_CONFIG)
    
    try:
        # Prepare journal entry lines
        entry_lines = []
        for line in lines:
            entry_lines.append((0, 0, {
                'account_id': line.get('account_id'),
                'debit': line.get('debit', 0),
                'credit': line.get('credit', 0),
                'name': line.get('name', reference)
            }))
        
        entry_id = client.execute_kw('account.move', 'create', [{
            'move_type': 'entry',
            'date': date,
            'ref': reference,
            'line_ids': entry_lines,
            'company_id': ODOO_CONFIG['company_id']
        }])
        
        log_message(f"Created journal entry {entry_id}")
        
        return {
            'entry_id': entry_id,
            'date': date,
            'reference': reference,
            'message': 'Journal entry created'
        }
        
    except Exception as e:
        return {'error': str(e)}


# ============================================================================
# MCP Server Implementation
# ============================================================================

class OdooAccountingMCPServer:
    """MCP Server for Odoo Accounting integration."""
    
    def __init__(self):
        self.tools = {
            'create_invoice': {
                'description': 'Create a new customer invoice in Odoo',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'partner_name': {'type': 'string', 'description': 'Customer name'},
                        'partner_email': {'type': 'string', 'description': 'Customer email'},
                        'lines': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'name': {'type': 'string'},
                                    'quantity': {'type': 'number'},
                                    'price': {'type': 'number'}
                                }
                            },
                            'description': 'Invoice lines'
                        },
                        'invoice_date': {'type': 'string', 'description': 'Invoice date (YYYY-MM-DD)'},
                        'payment_terms': {'type': 'string', 'description': 'Payment terms'}
                    },
                    'required': ['partner_name', 'partner_email', 'lines']
                }
            },
            'list_invoices': {
                'description': 'List invoices with optional filters',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'status': {'type': 'string', 'enum': ['draft', 'posted', 'cancel']},
                        'partner': {'type': 'string', 'description': 'Filter by partner name'},
                        'limit': {'type': 'integer', 'default': 20}
                    }
                }
            },
            'validate_invoice': {
                'description': 'Validate (post) a draft invoice',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'invoice_id': {'type': 'integer', 'description': 'Invoice ID'}
                    },
                    'required': ['invoice_id']
                }
            },
            'register_payment': {
                'description': 'Register a payment for an invoice',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'invoice_id': {'type': 'integer'},
                        'amount': {'type': 'number'},
                        'payment_date': {'type': 'string'},
                        'payment_reference': {'type': 'string'}
                    },
                    'required': ['invoice_id', 'amount']
                }
            },
            'list_customers': {
                'description': 'List all customers',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'limit': {'type': 'integer', 'default': 50}
                    }
                }
            },
            'list_vendors': {
                'description': 'List all vendors/suppliers',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'limit': {'type': 'integer', 'default': 50}
                    }
                }
            },
            'get_account_report': {
                'description': 'Get financial reports (P&L, Balance Sheet)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'report_type': {'type': 'string', 'enum': ['profit_loss', 'balance_sheet', 'trial_balance']},
                        'date_from': {'type': 'string'},
                        'date_to': {'type': 'string'}
                    }
                }
            },
            'create_journal_entry': {
                'description': 'Create a manual journal entry',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'date': {'type': 'string'},
                        'lines': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'account_id': {'type': 'integer'},
                                    'debit': {'type': 'number'},
                                    'credit': {'type': 'number'},
                                    'name': {'type': 'string'}
                                }
                            }
                        },
                        'reference': {'type': 'string'}
                    },
                    'required': ['date', 'lines']
                }
            }
        }
    
    def handle_request(self, request: dict) -> dict:
        """Handle an MCP JSON-RPC request."""
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        try:
            if method == 'tools/list':
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'tools': [
                            {'name': name, **tool}
                            for name, tool in self.tools.items()
                        ]
                    }
                }
            
            elif method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                
                result = self.call_tool(tool_name, arguments)
                
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'content': [{'type': 'text', 'text': json.dumps(result, indent=2, default=str)}]
                    }
                }
            
            elif method == 'initialize':
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'protocolVersion': '2024-11-05',
                        'capabilities': {'tools': {}},
                        'serverInfo': {'name': 'odoo-accounting-mcp', 'version': '1.0.0'}
                    }
                }
            
            else:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {'code': -32601, 'message': f'Method not found: {method}'}
                }
                
        except Exception as e:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {'code': -32603, 'message': str(e)}
            }
    
    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool by name."""
        tools_map = {
            'create_invoice': lambda args: create_invoice(
                partner_name=args.get('partner_name', ''),
                partner_email=args.get('partner_email', ''),
                lines=args.get('lines', []),
                invoice_date=args.get('invoice_date'),
                payment_terms=args.get('payment_terms')
            ),
            'list_invoices': lambda args: list_invoices(
                status=args.get('status'),
                partner=args.get('partner'),
                limit=args.get('limit', 20)
            ),
            'validate_invoice': lambda args: validate_invoice(
                invoice_id=args.get('invoice_id', 0)
            ),
            'register_payment': lambda args: register_payment(
                invoice_id=args.get('invoice_id', 0),
                amount=args.get('amount', 0),
                payment_date=args.get('payment_date'),
                payment_reference=args.get('payment_reference')
            ),
            'list_customers': lambda args: list_customers(
                limit=args.get('limit', 50)
            ),
            'list_vendors': lambda args: list_vendors(
                limit=args.get('limit', 50)
            ),
            'get_account_report': lambda args: get_account_report(
                report_type=args.get('report_type', 'profit_loss'),
                date_from=args.get('date_from'),
                date_to=args.get('date_to')
            ),
            'create_journal_entry': lambda args: create_journal_entry(
                date=args.get('date', ''),
                lines=args.get('lines', []),
                reference=args.get('reference', '')
            )
        }
        
        if name not in tools_map:
            return {'error': f'Unknown tool: {name}'}
        
        return tools_map[name](arguments)


def run_stdio_server():
    """Run the MCP server using stdio transport."""
    server = OdooAccountingMCPServer()
    log_message("Odoo Accounting MCP Server started")
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = server.handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            log_message(f"Invalid JSON: {e}", "ERROR")
        except Exception as e:
            log_message(f"Error: {e}", "ERROR")


def run_cli():
    """Run in CLI mode for testing."""
    print("Odoo Accounting MCP Server - CLI Mode")
    print("\nAvailable tools:")
    print("  create_invoice      - Create customer invoice")
    print("  list_invoices       - List invoices")
    print("  validate_invoice    - Validate draft invoice")
    print("  register_payment    - Register payment")
    print("  list_customers      - List customers")
    print("  list_vendors        - List vendors")
    print("  get_account_report  - Get financial reports")
    print("  create_journal_entry - Create journal entry")
    print("\nFor MCP integration, run without arguments for stdio mode.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        run_cli()
    else:
        run_stdio_server()
