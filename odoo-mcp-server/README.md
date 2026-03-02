# Odoo MCP Server

A Model Context Protocol (MCP) server for integrating with Odoo Community v19+ via JSON-RPC API. Supports draft invoice creation and payment logging with approval workflow.

## Features

- **Draft Invoice Creation**: Create invoices that remain in draft state until manually reviewed and posted
- **Payment Registration**: Log payments against invoices with automatic reconciliation
- **Approval Workflow**: Generates markdown files in `/Pending_Approval` before executing operations
- **JSON-RPC API**: Direct integration with Odoo Community v19+ using native JSON-RPC endpoints

## Installation

```bash
cd odoo-mcp-server
npm install
```

## Configuration

### Option 1: Config File

Copy the example config and edit:

```bash
cp config/odoo-config.json.example config/odoo-config.json
```

Edit `config/odoo-config.json`:

```json
{
  "baseUrl": "http://localhost:8069",
  "db": "odoo",
  "username": "admin",
  "password": "your_password",
  "companyId": null,
  "pendingApprovalDir": "./Pending_Approval"
}
```

### Option 2: Environment Variables

```bash
export ODOO_URL=http://localhost:8069
export ODOO_DB=odoo
export ODOO_USERNAME=admin
export ODOO_PASSWORD=your_password
export PENDING_APPROVAL_DIR=./Pending_Approval
```

## Available Tools

### 1. `odoo_create_draft_invoice`

Create a draft invoice in Odoo.

**Parameters:**
- `partnerId` (required): Partner/Customer ID
- `invoiceLineIds` (required): Array of line items
  - `name`: Description
  - `priceUnit`: Unit price
  - `quantity`: Quantity (default: 1)
  - `productId`: Product ID (optional)
  - `taxIds`: Array of tax IDs (optional)
- `invoiceDate`: Invoice date (YYYY-MM-DD)
- `dueDate`: Due date (YYYY-MM-DD)
- `paymentTermId`: Payment term ID
- `narrative`: Invoice notes
- `generateApprovalFile`: Generate markdown approval file (default: true)

**Example:**
```json
{
  "partnerId": 12,
  "invoiceDate": "2026-02-27",
  "invoiceLineIds": [
    {
      "name": "Consulting Services",
      "priceUnit": 150.00,
      "quantity": 10,
      "productId": 45
    }
  ],
  "narrative": "Monthly consulting services"
}
```

### 2. `odoo_register_payment`

Register a payment for an invoice.

**Parameters:**
- `invoiceId` (required): Invoice ID to pay
- `amount` (required): Payment amount
- `paymentDate`: Payment date (YYYY-MM-DD)
- `journalId`: Bank/Cash journal ID (auto-selected if not provided)
- `paymentReference`: Payment reference
- `communication`: Payment note
- `generateApprovalFile`: Generate markdown approval file (default: true)

**Example:**
```json
{
  "invoiceId": 105,
  "amount": 1500.00,
  "paymentDate": "2026-02-27",
  "paymentReference": "WIRE-2026-001",
  "communication": "Payment for Invoice INV/2026/0105"
}
```

### 3. `odoo_search_partner`

Search for partners/customers.

**Parameters:**
- `searchTerm`: Name, email, or VAT to search

### 4. `odoo_search_product`

Search for saleable products.

**Parameters:**
- `searchTerm`: Product name or code

### 5. `odoo_get_invoice`

Get invoice details by ID or reference.

**Parameters:**
- `identifier`: Invoice ID or reference number

### 6. `odoo_get_outstanding_invoices`

Get unpaid/partially paid invoices for a partner.

**Parameters:**
- `partnerId`: Partner ID

### 7. `odoo_get_payment_journals`

Get available bank/cash journals.

### 8. `odoo_get_taxes`

Get available sale taxes.

### 9. `odoo_get_payment_terms`

Get available payment terms.

## Approval Workflow

Before executing invoice creation or payment registration, the server generates a markdown file in the `/Pending_Approval` directory:

1. **Invoice Draft**: `INVOICE_DRAFT_<timestamp>.md`
2. **Payment Registration**: `PAYMENT_REG_<timestamp>.md`

These files contain:
- Complete operation details
- Line items and amounts
- Approval checkboxes
- Execution details

Review these files before approving the operation in your MCP client.

## Running the Server

### Direct Execution

```bash
npm start
```

### Development Mode

```bash
npm run dev
```

### MCP Client Configuration

Add to your MCP client config (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "odoo": {
      "command": "node",
      "args": ["D:/Personal Ai Employee/odoo-mcp-server/src/server.js"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "odoo",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "your_password"
      }
    }
  }
}
```

## Project Structure

```
odoo-mcp-server/
├── config/
│   ├── odoo-config.js          # Config loader
│   └── odoo-config.json.example # Example config
├── src/
│   ├── server.js               # Main MCP server
│   ├── odoo-client.js          # Odoo JSON-RPC client
│   ├── markdown-output.js      # Approval file generator
│   └── tools/
│       ├── invoice-tool.js     # Invoice operations
│       └── payment-tool.js     # Payment operations
├── Pending_Approval/           # Generated approval files
├── package.json
└── README.md
```

## API Endpoints Used

- `/web/session/authenticate` - Authentication
- `/web/dataset/call` - Model method execution

## Requirements

- Node.js 18+
- Odoo Community v19+
- Valid Odoo user credentials with appropriate permissions

## Permissions Required

The Odoo user needs:
- **Invoicing / Accounting** app access
- Create/Write permissions on:
  - `account.move` (Invoices)
  - `account.payment` (Payments)
  - `res.partner` (Partners - for search)
  - `product.template` (Products - for search)

## License

MIT
