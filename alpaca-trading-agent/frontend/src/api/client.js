/**
 * API Client for APEX — Alpaca AI Trading Agent backend
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
        } catch (e) {
          console.warn(`[API] Non-JSON response from ${endpoint}: ${text.slice(0, 100)}`);
          data = { _raw: text };
        }
      } else if (response.ok && response.status !== 204) {
        return { success: true, data: {}, note: 'Empty response' };
      }

      if (!response.ok) {
        const msg = data.detail || data.error || `HTTP ${response.status}`;
        throw new Error(msg);
      }
      return { success: true, data };
    } catch (error) {
      console.error(`[API] ${endpoint} failed:`, error);
      return { success: false, error: error.message || 'Unknown error' };
    }
  }

  get(endpoint) { return this.request(endpoint, { method: 'GET' }); }
  post(endpoint, body = {}) { return this.request(endpoint, { method: 'POST', body: JSON.stringify(body) }); }

  getHealth() { return this.get('/health'); }
  getAccount() { return this.get('/api/account'); }
  getPositions() { return this.get('/api/positions'); }
  getOrders() { return this.get('/api/orders'); }
  getPortfolioHistory(period = '1M', timeframe = '1D') { 
    return this.get(`/api/portfolio-history?period=${period}&timeframe=${timeframe}`); 
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

  async getChatHistory(sessionId) {
    return this.get(`/api/session/${sessionId}/history`);
  }

  startStrategy(config = null) { 
    return this.post('/api/strategy/start', config || { strategy_name: 'pairs_trading' }); 
  }
  stopStrategy() { return this.post('/api/strategy/stop'); }
}

export const apiClient = new APIClient();
