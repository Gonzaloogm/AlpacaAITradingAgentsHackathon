/**
 * API Client for Vantage — Alpaca AI Trading Agent backend
 */
export class APIClient {
  constructor() {
    this.baseURL = (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '') || import.meta.env.VITE_API_URL || 'http://localhost:8000';
  }

  async request(endpoint, options = {}) {
    try {
      const response = await fetch(this.baseURL + endpoint, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...options.headers },
      });

      const text = await response.text();
      let data = {};
      if (text) {
        try {
          data = JSON.parse(text);
        } catch {
          console.warn(`[API] Non-JSON response from ${endpoint}: ${text.slice(0, 100)}`);
          data = { _raw: text };
        }
      } else if (response.ok && response.status !== 204) {
        return { success: true, data: {}, note: 'Empty response' };
      }

      if (!response.ok) {
        const msg = data.detail || data.error || `HTTP ${response.status}`;
        if (!options.silent) {
          console.error(`[API] ${endpoint} failed:`, msg);
        }
        return { success: false, error: msg, status: response.status };
      }
      return { success: true, data };
    } catch (error) {
      if (!options.silent) {
        console.error(`[Network Error] ${endpoint}:`, error);
      }
      return { success: false, error: error.message };
    }
  }

  async get(endpoint, options = {}) { return this.request(endpoint, { method: 'GET', ...options }); }
  async post(endpoint, body = {}, options = {}) { return this.request(endpoint, { method: 'POST', body: JSON.stringify(body), ...options }); }

  getHealth() { return this.get('/api/system-status'); }
  getAccount() { return this.get('/api/account'); }
  getPositions() { return this.get('/api/positions'); }
  getOrders() { return this.get('/api/orders'); }
  getPortfolioHistory(period = '1M', timeframe = '1D') { 
    return this.get(`/api/portfolio-history?period=${period}&timeframe=${timeframe}`); 
  }
  getOHLC(symbol = 'SPY', timeframe = '1Day', limit = 60) {
    return this.get(`/api/ohlc/${symbol}?timeframe=${timeframe}&limit=${limit}`);
  }
  getAnalytics() {
    return this.get('/api/analytics');
  }
  getAgentState() { return this.get('/api/agent-state'); }
  
  getReasoningLog(limit = 50, offset = 0) { 
    return this.get(`/api/reasoning-log?limit=${limit}&offset=${offset}`); 
  }
  getReasoningSummary() { return this.get('/api/reasoning-log/summary'); }

  async sendChatMessage(sessionId, message) {
    return this.post('/api/chat', { session_id: sessionId, message });
  }

  async newChatSession() {
    return this.post('/api/session/new');
  }

  async getChatHistory(sessionId, options = {}) {
    return this.get(`/api/session/${sessionId}/history`, options);
  }

  startStrategy(config = null) { 
    return this.post('/api/strategy/start', config || { strategy_name: 'pairs_trading' }); 
  }
  stopStrategy() { return this.post('/api/strategy/stop'); }
}

export const apiClient = new APIClient();
