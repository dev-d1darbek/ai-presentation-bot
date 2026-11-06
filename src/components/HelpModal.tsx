import React from 'react';
import { X, HelpCircle, Check, Presentation, Mic, FileDown } from 'lucide-react';
import { AppLanguage } from '../types';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentLang: AppLanguage;
}

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose, currentLang }) => {
  if (!isOpen) return null;

  const content = {
    kk: {
      title: 'Көмек және Telegram Бот нұсқаулығы',
      desc: 'Бұл платформа веб-интерфейсте де, Telegram ботта да кез келген тақырыпта 30 кәсіби дизайнмен және таңдалған бет санымен дайын PowerPoint (.pptx) презентациясын жасайды.',
      features: [
        {
          title: '🤖 Telegram Ботта бет саны мен дизайн таңдау',
          text: 'Telegram ботқа тақырып жазғанда интерактивті баптау панелі ашылады: 📄 Бет санын (5–25 бет) және 🎨 30 дизайн стилінің бірін батырма арқылы таңдап, .PPTX файлын жүктей аласыз (/slides, /design, /settings).',
        },
        {
          title: '🎨 30 Кәсіби дизайн және веб-генератор',
          text: 'Тақырыпты енгізіп, слайдтар санын (5–25 бет) және дизайн стилін таңдаңыз. AI мазмұн мен дәйекті тезистерді толық құрастырады.',
        },
        {
          title: '📦 Сайтпен 1:1 сәйкес PPTX файлын жүктеу',
          text: 'Әр презентацияны PowerPoint (.pptx) форматында 16:9 кең экранды сапада бірден жүктеп алуға немесе Telegram-нан алуға болады.',
        },
        {
          title: '📚 Еркін қорғауға арналған кеңейтілген мазмұн',
          text: 'Әр слайдта тақырыпты еркін қорғауға жеткілікті толық аналитикалық мәтін, фактілер мен негізгі тезистер беріледі.',
        },
      ],
      closeBtn: 'Түсінікті',
    },
    ru: {
      title: 'Справка и руководство',
      desc: 'Это приложение позволяет создавать презентации в формате PPTX, генерировать план слайдов и готовый текст для устной защиты.',
      features: [
        {
          title: '🎨 Создание презентации',
          text: 'Укажите тему, количество слайдов, язык и стиль оформления. Искусственный интеллект сформирует логическую структуру и тезисы.',
        },
        {
          title: '📦 Экспорт в PowerPoint (.pptx)',
          text: 'Скачивайте готовую презентацию в формате 16:9 прямо на устройство и открывайте в Microsoft PowerPoint или Google Slides.',
        },
        {
          title: '🗣️ Текст для устной защиты',
          text: 'К каждому слайду формируются спикерские заметки и рекомендации для уверенного публичного выступления.',
        },
        {
          title: '📚 История презентаций',
          text: 'Все сгенерированные проекты сохраняются, позволяя быстро вернуться к ним или повторно скачать.',
        },
      ],
      closeBtn: 'Понятно',
    },
    en: {
      title: 'Help & Guide',
      desc: 'This application generates professional PPTX presentations, structured outlines, and ready-to-use speaker defense scripts on any topic.',
      features: [
        {
          title: '🎨 Presentation Builder',
          text: 'Choose your topic, slide count, language, and design aesthetic. AI plans the content and talking points automatically.',
        },
        {
          title: '📦 PowerPoint (.pptx) Export',
          text: 'Export directly to standard 16:9 widescreen PowerPoint files compatible with MS PowerPoint, Apple Keynote, and Google Slides.',
        },
        {
          title: '🗣️ Speaker Defense Script',
          text: 'Get tailored speaker notes and practical presentation advice for every slide to ace your oral presentation.',
        },
        {
          title: '📚 Presentation Library',
          text: 'Your generated presentations are saved in memory so you can revisit, edit, or re-download them anytime.',
        },
      ],
      closeBtn: 'Got it',
    },
  }[currentLang];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-750 w-full max-w-lg rounded-2xl shadow-2xl p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 text-sky-400">
            <HelpCircle className="w-5 h-5" />
            <h2 className="text-lg font-bold text-white">{content.title}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-slate-300 leading-relaxed">{content.desc}</p>

        <div className="space-y-3">
          {content.features.map((f, idx) => (
            <div key={idx} className="bg-slate-850 p-3.5 rounded-xl border border-slate-750 space-y-1">
              <h3 className="font-semibold text-white text-sm">{f.title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{f.text}</p>
            </div>
          ))}
        </div>

        <div className="pt-2">
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-semibold text-sm transition cursor-pointer"
          >
            {content.closeBtn}
          </button>
        </div>
      </div>
    </div>
  );
};
