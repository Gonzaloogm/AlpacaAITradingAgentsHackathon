import { useState, useEffect, useRef, useCallback } from 'react';
import { apiClient } from '../../api/client';
import LoadingSpinner from '../ui/LoadingSpinner';
import { Bot, User, Send, RefreshCw } from 'lucide-react';

const SESSION_KEY = 'vantage_agent_session_id';

const GREETING = {
  role: 'assistant',
  content: `Hello! I am Vantage, your AI trading assistant. 
You can ask me to analyze your portfolio, review open positions, or explain current market strategies.
*Example: "What are my current positions?" or "Explain your reasoning for the latest SPY/QQQ trade."*`,
};

export default function ChatInterface() {
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem(SESSION_KEY) || crypto.randomUUID();
  });
  
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    localStorage.setItem(SESSION_KEY, sessionId);
    (async () => {
      const result = await apiClient.getChatHistory(sessionId, { silent: true });
      if (result.success && result.data.history?.length > 0) {
        setMessages(result.data.history);
      } else if (!result.success && (result.status === 404 || (result.error && result.error.includes('not found')))) {
        // Recover gracefully from a stale session (e.g. backend restarted)
        const freshSessionId = crypto.randomUUID();
        localStorage.setItem(SESSION_KEY, freshSessionId);
        setSessionId(freshSessionId);
        setMessages([GREETING]);
      }
    })();
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const text = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    const result = await apiClient.sendChatMessage(sessionId, text);
    if (result.success) {
      if (result.data.session_id && result.data.session_id !== sessionId) {
        setSessionId(result.data.session_id);
      }
      setMessages(prev => [...prev, { role: 'assistant', content: result.data.response }]);
    } else {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${result.error}` }]);
    }
    setLoading(false);
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const handleReset = async () => {
    const result = await apiClient.newChatSession();
    if (result.success) {
      setSessionId(result.data.session_id);
      setMessages([GREETING]);
    }
  };

  return (
    <div className="bg-[#12141C] border border-white/5 rounded-xl flex flex-col h-[600px] shadow-lg overflow-hidden font-sans">
      <div className="flex justify-between items-center p-4 border-b border-white/5 bg-white/[0.01]">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-blue-500/10 text-blue-400"><Bot size={18} /></div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">Vantage Assistant</h3>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">Powered by Gemini</p>
          </div>
        </div>
        <button onClick={handleReset} className="p-2 text-slate-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-4 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${msg.role === 'user' ? 'bg-slate-700 text-white' : 'bg-blue-600 text-white'}`}>
              {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div className={`px-5 py-3.5 rounded-xl text-sm leading-relaxed shadow-sm ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-sm' : 'bg-white/[0.03] border border-white/5 text-slate-200 rounded-tl-sm'}`}>
              <div className="whitespace-pre-wrap">{msg.content}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-4 max-w-[85%]">
            <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center bg-blue-600 text-white"><Bot size={14} /></div>
            <div className="px-5 py-3.5 rounded-xl rounded-tl-sm bg-white/[0.03] border border-white/5 flex items-center gap-2">
              <LoadingSpinner size="sm" /> <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 bg-white/[0.01] border-t border-white/5">
        <div className="flex items-center gap-2 bg-black/20 border border-white/10 rounded-xl p-1 pr-2 focus-within:border-blue-500/50 transition-colors shadow-inner">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            disabled={loading}
            placeholder="Ask Vantage about your portfolio or strategy..."
            className="flex-1 bg-transparent px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="p-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-30 transition-all"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
