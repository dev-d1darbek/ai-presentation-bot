import React, { useState } from 'react';
import {
  Send,
  Sparkles,
  Bot,
  User,
  Wand2,
  Palette,
  Layers,
  Users,
  Loader2,
  X,
  RefreshCw,
} from 'lucide-react';
import { PresentationData, ChatMessage } from '../designs/types';
import { refinePresentationAPI } from '../services/api';

interface ChatRefineDrawerProps {
  presentation: PresentationData;
  onUpdatePresentation: (updated: PresentationData) => void;
  isOpen: boolean;
  onClose: () => void;
}

export const ChatRefineDrawer: React.FC<ChatRefineDrawerProps> = ({
  presentation,
  onUpdatePresentation,
  isOpen,
  onClose,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init',
      sender: 'assistant',
      text: `Сәлем! «${presentation.topic}» презентациясы дайын. Кез келген өзгерісті жазыңыз: мысалы, «3-слайдты өзгерт», «Екі адам туралы бөлім қос», «Дизайнын Apple Keynote-ке ауыстыр» немесе «Суреттерді көбейт».`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const sampleQuickPrompts = [
    { label: '👥 2 адамды салыстыру', text: 'Екі адамның өмірбаяны мен салыстырмалы талдауын қос' },
    { label: '✨ Заманауи дизайн', text: 'Дизайнын Apple Keynote стиліне ауыстыр' },
    { label: '📊 Көбірек статистика', text: 'Презентацияға нақты сандар мен метрикалар қос' },
    { label: '✍️ 3-слайдты тереңдет', text: '3-слайдтың мазмұнын тереңдетіп, фактілерді көбейт' },
  ];

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || isProcessing) return;

    const userMsg: ChatMessage = {
      id: 'msg_' + Date.now(),
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setIsProcessing(true);

    try {
      const res = await refinePresentationAPI({
        presentation,
        user_message: text,
      });

      onUpdatePresentation(res.presentation);

      const botReply: ChatMessage = {
        id: 'reply_' + Date.now(),
        sender: 'assistant',
        text: res.reply || 'Өзгерістер сәтті енгізілді!',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, botReply]);
    } catch (e: any) {
      const errorReply: ChatMessage = {
        id: 'err_' + Date.now(),
        sender: 'assistant',
        text: 'Кешіріңіз, сұранысты өңдеуде қате болды. Қайталап көріңізші.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorReply]);
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full sm:w-96 bg-slate-900 border-l border-slate-750 shadow-2xl flex flex-col animate-slide-left">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-850">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm">AI Редактор көмекшісі</h3>
            <p className="text-[11px] text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Контексті сақтап өңдейді
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-2.5 ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div
              className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs shrink-0 ${
                msg.sender === 'user'
                  ? 'bg-sky-600 text-white'
                  : 'bg-slate-800 text-sky-400 border border-slate-700'
              }`}
            >
              {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            <div
              className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
                msg.sender === 'user'
                  ? 'bg-sky-600 text-white rounded-tr-none'
                  : 'bg-slate-800 text-slate-200 border border-slate-700/80 rounded-tl-none'
              }`}
            >
              <p>{msg.text}</p>
              <span className="block text-[10px] text-slate-400/80 mt-1 text-right">
                {msg.timestamp}
              </span>
            </div>
          </div>
        ))}

        {isProcessing && (
          <div className="flex items-center gap-2 text-xs text-sky-400 bg-slate-800/60 p-3 rounded-xl border border-slate-700/50">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>AI презентацияға өзгерістер енгізуде...</span>
          </div>
        )}
      </div>

      {/* Quick Prompts */}
      <div className="p-3 bg-slate-850/60 border-t border-slate-800 space-y-1.5">
        <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
          💡 Жылдам түзету командалары:
        </p>
        <div className="flex flex-wrap gap-1.5">
          {sampleQuickPrompts.map((q) => (
            <button
              key={q.label}
              type="button"
              disabled={isProcessing}
              onClick={() => handleSendMessage(q.text)}
              className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition cursor-pointer"
            >
              {q.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="p-3 border-t border-slate-800 bg-slate-850">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Мысалы: 2-слайдты толықтыр..."
            disabled={isProcessing}
            className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
          <button
            type="submit"
            disabled={!inputMessage.trim() || isProcessing}
            className="p-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white transition cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
