import { OdooClient } from '../odoo-client.js';

/**
 * Create a draft invoice in Odoo
 * Invoice remains in draft state until explicitly posted
 */
export async function createDraftInvoice(client, invoiceData) {
  const {
    partnerId,
    invoiceDate,
    dueDate,
    invoiceLineIds,
    paymentTermId,
    fiscalPositionId,
    narrative,
    companyId
  } = invoiceData;

  // Validate required fields
  if (!partnerId) {
    throw new Error('partnerId is required');
  }

  if (!invoiceLineIds || invoiceLineIds.length === 0) {
    throw new Error('At least one invoice line is required');
  }

  // Prepare invoice values for draft state
  const invoiceValues = {
    move_type: 'out_invoice',
    partner_id: partnerId,
    invoice_date: invoiceDate || new Date().toISOString().split('T')[0],
    invoice_date_due: dueDate || null,
    invoice_line_ids: invoiceLineIds.map(line => [0, 0, {
      product_id: line.productId,
      name: line.name || line.description,
      quantity: line.quantity || 1,
      price_unit: line.priceUnit || line.price_unit || 0,
      tax_ids: line.taxIds ? line.taxIds.map(taxId => [6, 0, [taxId]]) : [],
      analytic_distribution: line.analyticDistribution || {}
    }]),
    payment_term_id: paymentTermId || null,
    fiscal_position_id: fiscalPositionId || null,
    narrative: narrative || null,
    company_id: companyId || null,
    // Ensure invoice stays in draft
    state: 'draft'
  };

  // Create the invoice via Odoo API
  const invoiceId = await client.create('account.move', invoiceValues);

  return {
    success: true,
    invoiceId,
    message: `Draft invoice ${invoiceId} created successfully`,
    status: 'draft'
  };
}

/**
 * Search for partners by name or email
 */
export async function searchPartner(client, searchTerm) {
  const domain = [
    ['active', '=', true],
    ['customer_rank', '>', 0]
  ];

  if (searchTerm) {
    domain.push([
      '|', '|',
      ['name', 'ilike', searchTerm],
      ['email', 'ilike', searchTerm],
      ['vat', 'ilike', searchTerm]
    ]);
  }

  const partners = await client.search('res.partner', domain, {
    fields: ['id', 'name', 'email', 'phone', 'vat', 'street', 'city', 'country_id'],
    limit: 20
  });

  return partners;
}

/**
 * Search for products
 */
export async function searchProduct(client, searchTerm) {
  const domain = [
    ['active', '=', true],
    ['sale_ok', '=', true]
  ];

  if (searchTerm) {
    domain.push([
      '|',
      ['name', 'ilike', searchTerm],
      ['default_code', 'ilike', searchTerm]
    ]);
  }

  const products = await client.search('product.template', domain, {
    fields: ['id', 'name', 'default_code', 'list_price', 'uom_name', 'taxes_id'],
    limit: 20
  });

  return products;
}

/**
 * Get available taxes
 */
export async function getTaxes(client) {
  const taxes = await client.search('account.tax', [
    ['active', '=', true],
    ['type_tax_use', '=', 'sale']
  ], {
    fields: ['id', 'name', 'amount', 'amount_type', 'type_tax_use'],
    limit: 50
  });

  return taxes;
}

/**
 * Get payment terms
 */
export async function getPaymentTerms(client) {
  const terms = await client.search('account.payment.term', [
    ['active', '=', true]
  ], {
    fields: ['id', 'name', 'note'],
    limit: 50
  });

  return terms;
}

export default {
  createDraftInvoice,
  searchPartner,
  searchProduct,
  getTaxes,
  getPaymentTerms
};
