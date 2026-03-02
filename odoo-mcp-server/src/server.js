#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { OdooClient } from './odoo-client.js';
import loadConfig from '../config/odoo-config.js';
import MarkdownOutputGenerator from './markdown-output.js';
import { createDraftInvoice, searchPartner, searchProduct, getTaxes, getPaymentTerms } from './tools/invoice-tool.js';
import { registerPayment, getOutstandingInvoices, getPaymentJournals, getPaymentMethods, getInvoice } from './tools/payment-tool.js';

// Load configuration
const config = loadConfig();

// Initialize Odoo client
let odooClient = null;

// Initialize markdown output generator
const markdownGenerator = new MarkdownOutputGenerator(config.pendingApprovalDir);

// Initialize MCP Server
const server = new Server(
  {
    name: 'odoo-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Get or create Odoo client
 */
function getOdooClient() {
  if (!odooClient) {
    odooClient = new OdooClient(config);
  }
  return odooClient;
}

/**
 * Tool definitions
 */
const TOOLS = [
  {
    name: 'odoo_create_draft_invoice',
    description: 'Create a draft invoice in Odoo. Invoice remains in draft state until manually posted. Generates markdown file in /Pending_Approval before execution.',
    inputSchema: {
      type: 'object',
      properties: {
        partnerId: {
          type: 'integer',
          description: 'Partner/Customer ID in Odoo'
        },
        invoiceDate: {
          type: 'string',
          description: 'Invoice date (YYYY-MM-DD format). Defaults to today.'
        },
        dueDate: {
          type: 'string',
          description: 'Due date (YYYY-MM-DD format)'
        },
        invoiceLineIds: {
          type: 'array',
          description: 'Array of invoice line items',
          items: {
            type: 'object',
            properties: {
              productId: {
                type: 'integer',
                description: 'Product ID'
              },
              name: {
                type: 'string',
                description: 'Line description'
              },
              quantity: {
                type: 'number',
                description: 'Quantity',
                default: 1
              },
              priceUnit: {
                type: 'number',
                description: 'Unit price'
              },
              taxIds: {
                type: 'array',
                description: 'Array of tax IDs',
                items: { type: 'integer' }
              }
            },
            required: ['name', 'priceUnit']
          }
        },
        paymentTermId: {
          type: 'integer',
          description: 'Payment term ID'
        },
        fiscalPositionId: {
          type: 'integer',
          description: 'Fiscal position ID'
        },
        narrative: {
          type: 'string',
          description: 'Invoice notes/narrative'
        },
        companyId: {
          type: 'integer',
          description: 'Company ID (defaults to user\'s company)'
        },
        generateApprovalFile: {
          type: 'boolean',
          description: 'Generate markdown approval file before execution',
          default: true
        }
      },
      required: ['partnerId', 'invoiceLineIds']
    }
  },
  {
    name: 'odoo_register_payment',
    description: 'Register a payment for an invoice in Odoo. Generates markdown file in /Pending_Approval before execution.',
    inputSchema: {
      type: 'object',
      properties: {
        invoiceId: {
          type: 'integer',
          description: 'Invoice ID to pay'
        },
        amount: {
          type: 'number',
          description: 'Payment amount'
        },
        paymentDate: {
          type: 'string',
          description: 'Payment date (YYYY-MM-DD format). Defaults to today.'
        },
        paymentMethodId: {
          type: 'integer',
          description: 'Payment method ID'
        },
        journalId: {
          type: 'integer',
          description: 'Bank/Cash journal ID. Auto-selected if not provided.'
        },
        paymentReference: {
          type: 'string',
          description: 'Payment reference'
        },
        communication: {
          type: 'string',
          description: 'Payment communication/note'
        },
        companyId: {
          type: 'integer',
          description: 'Company ID'
        },
        generateApprovalFile: {
          type: 'boolean',
          description: 'Generate markdown approval file before execution',
          default: true
        }
      },
      required: ['invoiceId', 'amount']
    }
  },
  {
    name: 'odoo_search_partner',
    description: 'Search for partners/customers in Odoo by name, email, or VAT',
    inputSchema: {
      type: 'object',
      properties: {
        searchTerm: {
          type: 'string',
          description: 'Search term (name, email, or VAT)'
        }
      }
    }
  },
  {
    name: 'odoo_search_product',
    description: 'Search for saleable products in Odoo',
    inputSchema: {
      type: 'object',
      properties: {
        searchTerm: {
          type: 'string',
          description: 'Product name or code to search'
        }
      }
    }
  },
  {
    name: 'odoo_get_invoice',
    description: 'Get invoice details by ID or reference number',
    inputSchema: {
      type: 'object',
      properties: {
        identifier: {
          type: 'string',
          description: 'Invoice ID or reference number'
        }
      },
      required: ['identifier']
    }
  },
  {
    name: 'odoo_get_outstanding_invoices',
    description: 'Get outstanding (unpaid/partially paid) invoices for a partner',
    inputSchema: {
      type: 'object',
      properties: {
        partnerId: {
          type: 'integer',
          description: 'Partner ID'
        }
      },
      required: ['partnerId']
    }
  },
  {
    name: 'odoo_get_payment_journals',
    description: 'Get available bank/cash journals for payments',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'odoo_get_taxes',
    description: 'Get available sale taxes',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'odoo_get_payment_terms',
    description: 'Get available payment terms',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  }
];

/**
 * Handle tool calls
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const client = getOdooClient();

  try {
    // Ensure connection
    await client.authenticate();

    switch (name) {
      case 'odoo_create_draft_invoice': {
        const { generateApprovalFile = true, ...invoiceData } = args;

        // Generate approval file first
        if (generateApprovalFile) {
          const approvalResult = await markdownGenerator.generateInvoiceDraft(invoiceData);
          console.error(`Approval file generated: ${approvalResult.filepath}`);
        }

        // Create the draft invoice
        const result = await createDraftInvoice(client, invoiceData);

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2)
            }
          ]
        };
      }

      case 'odoo_register_payment': {
        const { generateApprovalFile = true, ...paymentData } = args;

        // Generate approval file first
        if (generateApprovalFile) {
          const approvalResult = await markdownGenerator.generatePaymentDraft(paymentData);
          console.error(`Approval file generated: ${approvalResult.filepath}`);
        }

        // Register the payment
        const result = await registerPayment(client, paymentData);

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2)
            }
          ]
        };
      }

      case 'odoo_search_partner': {
        const partners = await searchPartner(client, args.searchTerm);
        return {
          content: [{ type: 'text', text: JSON.stringify(partners, null, 2) }]
        };
      }

      case 'odoo_search_product': {
        const products = await searchProduct(client, args.searchTerm);
        return {
          content: [{ type: 'text', text: JSON.stringify(products, null, 2) }]
        };
      }

      case 'odoo_get_invoice': {
        const invoice = await getInvoice(client, args.identifier);
        return {
          content: [{ type: 'text', text: JSON.stringify(invoice || { error: 'Invoice not found' }, null, 2) }]
        };
      }

      case 'odoo_get_outstanding_invoices': {
        const invoices = await getOutstandingInvoices(client, args.partnerId, config.companyId);
        return {
          content: [{ type: 'text', text: JSON.stringify(invoices, null, 2) }]
        };
      }

      case 'odoo_get_payment_journals': {
        const journals = await getPaymentJournals(client, config.companyId);
        return {
          content: [{ type: 'text', text: JSON.stringify(journals, null, 2) }]
        };
      }

      case 'odoo_get_taxes': {
        const taxes = await getTaxes(client);
        return {
          content: [{ type: 'text', text: JSON.stringify(taxes, null, 2) }]
        };
      }

      case 'odoo_get_payment_terms': {
        const terms = await getPaymentTerms(client);
        return {
          content: [{ type: 'text', text: JSON.stringify(terms, null, 2) }]
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ error: error.message }, null, 2)
        }
      ],
      isError: true
    };
  }
});

/**
 * Handle tool list request
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: TOOLS
  };
});

/**
 * Start the server
 */
async function main() {
  try {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('Odoo MCP Server running on stdio');
    console.error(`Connected to: ${config.baseUrl}`);
    console.error(`Pending Approval Dir: ${config.pendingApprovalDir}`);
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

main();
