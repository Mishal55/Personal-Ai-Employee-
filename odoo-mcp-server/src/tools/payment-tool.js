import { OdooClient } from '../odoo-client.js';

/**
 * Register a payment for an invoice in Odoo
 * Creates a payment entry and reconciles with the invoice
 */
export async function registerPayment(client, paymentData) {
  const {
    invoiceId,
    amount,
    paymentDate,
    paymentMethodId,
    journalId,
    paymentReference,
    communication,
    companyId
  } = paymentData;

  // Validate required fields
  if (!invoiceId) {
    throw new Error('invoiceId is required');
  }

  if (!amount || amount <= 0) {
    throw new Error('Valid payment amount is required');
  }

  // First, get the invoice details to determine partner and company
  const invoice = await client.read('account.move', invoiceId, [
    'partner_id',
    'company_id',
    'currency_id',
    'amount_total',
    'amount_residual',
    'state',
    'payment_state'
  ]);

  if (!invoice) {
    throw new Error(`Invoice ${invoiceId} not found`);
  }

  if (invoice.state === 'draft') {
    throw new Error(`Cannot register payment for draft invoice ${invoiceId}. Invoice must be posted first.`);
  }

  // Get default journal if not specified
  let effectiveJournalId = journalId;
  if (!effectiveJournalId) {
    const journals = await client.search('account.journal', [
      ['type', '=', 'bank'],
      ['company_id', '=', invoice.company_id?.[0] || companyId],
      ['active', '=', true]
    ], {
      fields: ['id', 'name', 'type'],
      limit: 1
    });
    effectiveJournalId = journals[0]?.id;
  }

  if (!effectiveJournalId) {
    throw new Error('No bank journal found. Please specify a journalId.');
  }

  // Create payment using account.payment.register wizard approach
  // For Odoo 19+, we create the payment directly
  const paymentValues = {
    date: paymentDate || new Date().toISOString().split('T')[0],
    payment_type: 'inbound',
    partner_type: 'customer',
    partner_id: invoice.partner_id?.[0],
    amount: amount,
    currency_id: invoice.currency_id?.[0],
    journal_id: effectiveJournalId,
    payment_method_id: paymentMethodId || null,
    ref: paymentReference || `Payment for Invoice ${invoiceId}`,
    communication: communication || invoice.ref || `Invoice ${invoiceId}`,
    company_id: companyId || invoice.company_id?.[0],
    // Link to invoice
    move_id: invoiceId,
    paid_move_ids: [[6, 0, [invoiceId]]]
  };

  const paymentId = await client.create('account.payment', paymentValues);

  // Confirm the payment
  await client.execute('account.payment', 'action_post', [[paymentId]]);

  return {
    success: true,
    paymentId,
    invoiceId,
    amount,
    message: `Payment ${paymentId} of ${amount} registered for invoice ${invoiceId}`,
    paymentState: invoice.payment_state
  };
}

/**
 * Get outstanding payments for a partner
 */
export async function getOutstandingInvoices(client, partnerId, companyId) {
  const domain = [
    ['move_type', '=', 'out_invoice'],
    ['state', '=', 'posted'],
    ['payment_state', '!=', 'paid'],
    ['partner_id', '=', partnerId]
  ];

  if (companyId) {
    domain.push(['company_id', '=', companyId]);
  }

  const invoices = await client.search('account.move', domain, {
    fields: [
      'id',
      'name',
      'partner_id',
      'invoice_date',
      'invoice_date_due',
      'amount_total',
      'amount_residual',
      'payment_state',
      'currency_id'
    ],
    order: 'invoice_date_due ASC'
  });

  return invoices;
}

/**
 * Get available payment journals
 */
export async function getPaymentJournals(client, companyId) {
  const domain = [
    ['type', 'in', ['bank', 'cash']],
    ['active', '=', true]
  ];

  if (companyId) {
    domain.push(['company_id', '=', companyId]);
  }

  const journals = await client.search('account.journal', domain, {
    fields: ['id', 'name', 'type', 'code', 'currency_id'],
    limit: 50
  });

  return journals;
}

/**
 * Get payment methods
 */
export async function getPaymentMethods(client, journalId) {
  const domain = journalId ? [['journal_id', '=', journalId]] : [];
  
  const methods = await client.search('account.payment.method', domain, {
    fields: ['id', 'name', 'payment_type'],
    limit: 50
  });

  return methods;
}

/**
 * Get invoice by reference or ID
 */
export async function getInvoice(client, identifier) {
  let invoice = null;

  // Try to find by ID first (numeric)
  if (typeof identifier === 'number' || /^\d+$/.test(identifier)) {
    const id = parseInt(identifier);
    invoice = await client.read('account.move', id, [
      'id',
      'name',
      'partner_id',
      'invoice_date',
      'invoice_date_due',
      'amount_total',
      'amount_residual',
      'payment_state',
      'state',
      'currency_id',
      'ref',
      'narrative',
      'invoice_line_ids'
    ]);
  }

  // If not found, try by name/reference
  if (!invoice) {
    const invoices = await client.search('account.move', [
      ['name', '=', identifier]
    ], {
      fields: ['id', 'name', 'partner_id', 'amount_total', 'payment_state'],
      limit: 1
    });
    if (invoices.length > 0) {
      invoice = await client.read('account.move', invoices[0].id, [
        'id', 'name', 'partner_id', 'invoice_date', 'invoice_date_due',
        'amount_total', 'amount_residual', 'payment_state', 'state',
        'currency_id', 'ref', 'narrative'
      ]);
    }
  }

  return invoice;
}

export default {
  registerPayment,
  getOutstandingInvoices,
  getPaymentJournals,
  getPaymentMethods,
  getInvoice
};
