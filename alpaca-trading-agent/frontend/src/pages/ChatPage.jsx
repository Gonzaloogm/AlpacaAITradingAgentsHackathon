import ChatInterface from '../components/chat/ChatInterface';
import { MessageSquare, ShieldCheck, Cpu } from 'lucide-react';

export default function ChatPage() {
  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-[#161920] border border-white/5 rounded-2xl p-6">
        <div>
          <div className="flex items-center gap-2">
            <MessageSquare size={20} className="text-[#00BFA5]" />
            <h1 className="text-xl font-bold text-white tracking-wide">Interactive AI Agent Assistant</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Chat directly with the AI Agent. Ask about portfolio status, strategy reasoning, or issue trade instructions via Alpaca MCP tools.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono text-slate-400 bg-white/5 px-4 py-2 rounded-xl border border-white/5">
          <Cpu size={14} className="text-purple-400" />
          <span>Gemini 3.6 Flash / Claude Tool Loop Active</span>
        </div>
      </div>

      <div className="bg-[#11141D] border border-white/5 rounded-2xl p-6 shadow-2xl h-[650px]">
        <ChatInterface />
      </div>
    </div>
  );
}
