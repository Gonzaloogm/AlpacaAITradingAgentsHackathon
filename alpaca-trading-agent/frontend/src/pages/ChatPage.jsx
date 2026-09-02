import ChatInterface from '../components/chat/ChatInterface';
import { MessageSquare } from 'lucide-react';

export default function ChatPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12 font-sans">
      <div className="flex justify-between items-center bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <MessageSquare className="text-blue-500" /> Vantage Assistant
          </h1>
          <p className="text-sm text-slate-400 mt-1">Interact directly with your AI trading agent to analyze strategy and positions.</p>
        </div>
      </div>
      <ChatInterface />
    </div>
  );
}
