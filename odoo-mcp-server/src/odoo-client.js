import http from 'http';
import https from 'https';

/**
 * Odoo JSON-RPC Client for Community v19+
 * Handles authentication and API calls via JSON-RPC
 */
export class OdooClient {
  constructor(config) {
    this.baseUrl = config.baseUrl?.replace(/\/$/, '');
    this.db = config.db;
    this.username = config.username;
    this.password = config.password;
    this.uid = null;
    this.sessionId = null;
  }

  /**
   * Make a JSON-RPC request to Odoo
   */
  async jsonRpcRequest(endpoint, params) {
    const url = `${this.baseUrl}${endpoint}`;
    const payload = {
      jsonrpc: '2.0',
      method: 'call',
      params: params || {},
      id: Math.floor(Math.random() * 1000000)
    };

    return new Promise((resolve, reject) => {
      const data = JSON.stringify(payload);
      const isHttps = url.startsWith('https://');
      const lib = isHttps ? https : http;

      const options = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': data.length,
          ...(this.sessionId ? { Cookie: this.sessionId } : {})
        }
      };

      const req = lib.request(url, options, (res) => {
        let responseData = '';
        res.on('data', chunk => responseData += chunk);
        res.on('end', () => {
          try {
            const result = JSON.parse(responseData);
            if (result.error) {
              reject(new Error(result.error.data?.message || result.error.message || 'Odoo API Error'));
            } else {
              resolve(result.result);
            }
          } catch (e) {
            reject(new Error(`Failed to parse response: ${e.message}`));
          }
        });
      });

      req.on('error', reject);
      req.write(data);
      req.end();
    });
  }

  /**
   * Authenticate with Odoo and get session
   */
  async authenticate() {
    try {
      const result = await this.jsonRpcRequest('/web/session/authenticate', {
        db: this.db,
        login: this.username,
        password: this.password
      });

      if (result.uid) {
        this.uid = result.uid;
        // Extract session cookie
        const setCookie = result.user_context?.http_session_id;
        if (setCookie) {
          this.sessionId = `session_id=${setCookie}`;
        }
        return { success: true, uid: this.uid };
      }
      return { success: false, error: 'Authentication failed' };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Execute Odoo model method
   */
  async execute(model, method, args = [], kwargs = {}) {
    if (!this.uid) {
      await this.authenticate();
    }

    return await this.jsonRpcRequest('/web/dataset/call', {
      model,
      method,
      args,
      kwargs
    });
  }

  /**
   * Search for records
   */
  async search(model, domain = [], options = {}) {
    return await this.execute(model, 'search_read', [domain], {
      fields: options.fields || [],
      limit: options.limit,
      offset: options.offset,
      order: options.order
    });
  }

  /**
   * Create a record
   */
  async create(model, values) {
    return await this.execute(model, 'create', [values]);
  }

  /**
   * Write/update a record
   */
  async write(model, id, values) {
    return await this.execute(model, 'write', [[id], values]);
  }

  /**
   * Get record by ID
   */
  async read(model, id, fields = []) {
    const result = await this.execute(model, 'read', [[id]], { fields });
    return result[0] || null;
  }

  /**
   * Get current user's company
   */
  async getCurrentCompany() {
    if (!this.uid) {
      await this.authenticate();
    }
    const user = await this.read('res.users', this.uid, ['company_id', 'company_ids']);
    return user?.company_id?.[0] || null;
  }
}

export default OdooClient;
