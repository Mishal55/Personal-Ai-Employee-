import { readFileSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Load Odoo configuration from config file or environment variables
 */
export function loadConfig() {
  const configPath = join(__dirname, '..', 'config', 'odoo-config.json');
  
  let config = {};
  
  // Try to load from config file first
  if (existsSync(configPath)) {
    try {
      const fileContent = readFileSync(configPath, 'utf-8');
      config = JSON.parse(fileContent);
    } catch (e) {
      console.error('Warning: Could not parse config file:', e.message);
    }
  }
  
  // Override with environment variables if present
  return {
    baseUrl: process.env.ODOO_URL || config.baseUrl || 'http://localhost:8069',
    db: process.env.ODOO_DB || config.db || 'odoo',
    username: process.env.ODOO_USERNAME || config.username || 'admin',
    password: process.env.ODOO_PASSWORD || config.password || '',
    companyId: process.env.ODOO_COMPANY_ID || config.companyId || null,
    pendingApprovalDir: process.env.PENDING_APPROVAL_DIR || 
      config.pendingApprovalDir || 
      join(__dirname, '..', 'Pending_Approval')
  };
}

export default loadConfig;
