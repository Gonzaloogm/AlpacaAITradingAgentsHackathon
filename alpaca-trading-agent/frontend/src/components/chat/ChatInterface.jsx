import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { apiClient } from '../../api/client';
import LoadingSpinner from '../ui/LoadingSpinner';
import { Bot, User, Send, RefreshCw, Wrench, Sparkles } from 'lucide-react';

const SESSION_KEY = 'vantage_agent_session_id';

const QUICK_PROMPTS = [
  "What are my current open positions?",
  "What is my buying power and cash balance?",
  "Analyze current SPY and QQQ spread",
  "Explain the active pairs trading strategy",
];

const GREETING = {
  role: 'assistant',
  content: `Hello! I am **Vantage**, your AI trading assistant powered by **Gemini 3.6 Flash** and the **Alpaca MCP Server**.

I have direct access to your brokerage account via 60+ Alpaca MCP tools. You can ask me to:
- 📊 **Inspect positions & orders:** *"What are my active positions?"*
- 💰 **Check portfolio balances:** *"What is my available buying power?"*
- ⚡ **Market analysis:** *"Analyze the current SPY / QQQ price spread"*
- 🧠 **Strategy explanation:** *"Explain your reasoning for the latest trade cycle"*`,
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

  const sendMessage = async (overrideText = null) => {
    const text = (overrideText || input).trim();
    if (!text || loading) return;
    if (!overrideText) setInput('');

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    const result = await apiClient.sendChatMessage(sessionId, text);
    if (result.success) {
      if (result.data.session_id && result.data.session_id !== sessionId) {
        setSessionId(result.data.session_id);
      }
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: result.data.response,
          tool_calls: result.data.tool_calls || [],
        },
      ]);
    } else {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `⚠️ Error processing request: ${result.error}` },
      ]);
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
    <div className="bg-[#12141C] border border-white/5 rounded-xl flex flex-col h-[650px] shadow-lg overflow-hidden font-sans">
      {/* Header */}
      <div className="flex justify-between items-center p-4 border-b border-white/5 bg-white/[0.01]">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Bot size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-wide">Vantage Assistant</h3>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                Alpaca MCP Connected
              </span>
            </div>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest mt-0.5">
              Powered by Gemini 3.6 Flash · Tool Use Enabled
            </p>
          </div>
        </div>
        <button
          onClick={handleReset}
          title="Reset conversation"
          className="p-2 text-slate-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, i) => {
          const isUser = msg.role === 'user';
          const toolCalls = Array.isArray(msg.tool_calls) ? msg.tool_calls : [];

          return (
            <div
              key={i}
              className={`flex gap-3 max-w-[88%] ${isUser ? 'ml-auto flex-row-reverse' : ''}`}
            >
              <div
                className={`w-8 h-8 rounded-xl flex-shrink-0 flex items-center justify-center text-white ${
                  isUser ? 'bg-slate-700' : 'bg-blue-600 shadow-md shadow-blue-500/20'
                }`}
              >
                {isUser ? <User size={14} /> : <Bot size={14} />}
              </div>

              <div
                className={`px-5 py-3.5 rounded-2xl text-sm leading-relaxed shadow-sm ${
                  isUser
                    ? 'bg-blue-600 text-white rounded-tr-sm'
                    : 'bg-[#0B0E14] border border-white/5 text-slate-200 rounded-tl-sm'
                }`}
              >
                {/* Message Body with Markdown */}
                <div className="prose prose-invert prose-sm max-w-none text-slate-200 break-words font-sans">
                  {isUser ? (
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  ) : (
                    <ReactMarkdown
                      components={{
                        p: (props) => <p className="mb-2 last:mb-0" {...props} />,
                        ul: (props) => <ul className="list-disc pl-4 mb-2 space-y-1" {...props} />,
                        ol: (props) => <ol className="list-decimal pl-4 mb-2 space-y-1" {...props} />,
                        code: (props) => (
                          <code className="bg-black/40 text-blue-300 font-mono text-xs px-1 py-0.5 rounded" {...props} />
                        ),
                        table: (props) => (
                          <div className="overflow-x-auto my-2">
                            <table className="w-full text-xs font-mono border-collapse border border-white/10" {...props} />
                          </div>
                        ),
                        th: (props) => (
                          <th className="border border-white/10 bg-white/5 px-2 py-1 text-left font-bold text-white" {...props} />
                        ),
                        td: (props) => (
                          <td className="border border-white/10 px-2 py-1 text-slate-300" {...props} />
                        ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  )}
                </div>

                {/* MCP Tool Invocations Badge Block */}
                {toolCalls.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/10 space-y-2">
                    <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold text-cyan-400">
                      <Wrench size={12} />
                      <span>Alpaca MCP Tools Executed ({toolCalls.length})</span>
                    </div>
                    <div className="space-y-1.5">
                      {toolCalls.map((tc, tIdx) => (
                        <div
                          key={tIdx}
                          className="bg-black/40 border border-white/5 rounded-lg p-2.5 text-xs font-mono space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-cyan-300 font-bold">⚡ {tc.name || 'MCP Tool'}</span>
                          </div>
                          {tc.args && Object.keys(tc.args).length > 0 && (
                            <div className="text-[10px] text-slate-400">
                              <span className="text-slate-500">Args: </span>
                              <code>{JSON.stringify(tc.args)}</code>
                            </div>
                          )}
                          {tc.result && (
                            <div className="mt-1">
                              <span className="text-[9px] text-slate-500 block uppercase">Result:</span>
                              <pre className="text-[10px] text-slate-300 bg-black/60 p-1.5 rounded overflow-x-auto max-h-24 scrollbar-thin">
                                {typeof tc.result === 'object'
                                  ? JSON.stringify(tc.result, null, 2)
                                  : String(tc.result)}
                              </pre>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex gap-3 max-w-[88%]">
            <div className="w-8 h-8 rounded-xl flex-shrink-0 flex items-center justify-center bg-blue-600 text-white shadow-md shadow-blue-500/20">
              <Bot size={14} />
            </div>
            <div className="px-5 py-3.5 rounded-2xl rounded-tl-sm bg-[#0B0E14] border border-white/5 flex items-center gap-2">
              <LoadingSpinner size="sm" />
              <span className="text-xs font-mono text-slate-400 uppercase tracking-widest">
                Analyzing market via MCP...
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick Action Prompt Pills */}
      <div className="px-4 py-2 bg-white/[0.01] border-t border-white/5 flex items-center gap-2 overflow-x-auto scrollbar-none">
        <Sparkles size={13} className="text-blue-400 flex-shrink-0" />
        {QUICK_PROMPTS.map((prompt, pIdx) => (
          <button
            key={pIdx}
            onClick={() => sendMessage(prompt)}
            disabled={loading}
            className="flex-shrink-0 text-[11px] font-mono text-slate-400 hover:text-white bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 px-2.5 py-1 rounded-full transition-all disabled:opacity-40 whitespace-nowrap"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <div className="p-4 bg-white/[0.01] border-t border-white/5">
        <div className="flex items-center gap-2 bg-[#0B0E14] border border-white/10 rounded-xl p-1.5 pr-2 focus-within:border-blue-500/50 transition-colors shadow-inner">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            disabled={loading}
            placeholder="Ask Vantage about your portfolio, strategy, or orders..."
            className="flex-1 bg-transparent px-4 py-2 text-sm text-white placeholder-slate-500 outline-none disabled:opacity-50 font-sans"
          />
          <button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            className="p-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-30 transition-all shadow-md shadow-blue-600/20"
          >
            <Send size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}
