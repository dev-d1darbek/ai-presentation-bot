import React from 'react';
import { Presentation as PresentationIcon, Sparkles, FolderOpen, HelpCircle, PlusCircle, Palette } from 'lucide-react';
import { AppLanguage } from '../types';

interface HeaderProps {
  currentLang: AppLanguage;
  onSelectLang: (lang: AppLanguage) => void;
  onNewPresentation: () => void;
  onOpenMyPresentations: () => void;
  onOpenThemesGallery: () => void;
  onOpenHelp: () => void;
  presentationCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  currentLang,
  onSelectLang,
  onNewPresentation,
  onOpenMyPresentations,
  onOpenThemesGallery,
  onOpenHelp,
  presentationCount,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/95 backdrop-blur sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-2">
        {/* Brand */}
        <div className="flex items-center gap-2 sm:gap-3 cursor-pointer min-w-0 shrink-0" onClick={onNewPresentation}>
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl sm:rounded-2xl bg-gradient-to-tr from-sky-500 via-teal-400 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20 shrink-0">
            <PresentationIcon className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-sm sm:text-lg text-white tracking-tight whitespace-nowrap">
                AI Presentation
              </span>
              <span className="hidden sm:inline-block text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-r from-sky-500 to-indigo-500 text-white font-extrabold tracking-wide uppercase shadow-xs">
                PRO
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">Кәсіби презентация генераторы • 30 дизайн</p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1 sm:gap-2.5 shrink-0">
          {/* 30 Themes Gallery Button */}
          <button
            onClick={onOpenThemesGallery}
            className="flex items-center gap-1.5 p-1.5 sm:px-3 sm:py-1.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs sm:text-sm font-medium border border-slate-700 transition cursor-pointer"
            title="30 Дизайн"
          >
            <Palette className="w-4 h-4 text-sky-400" />
            <span className="hidden sm:inline">30 Дизайн</span>
          </button>

          {/* New Presentation Button */}
          <button
            onClick={onNewPresentation}
            className="flex items-center gap-1.5 p-1.5 sm:px-3 sm:py-1.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs sm:text-sm font-semibold transition shadow-sm cursor-pointer"
            title="Жаңа жасау"
          >
            <PlusCircle className="w-4 h-4" />
            <span className="hidden sm:inline">Жаңа жасау</span>
          </button>

          {/* My Presentations */}
          <button
            onClick={onOpenMyPresentations}
            className="flex items-center gap-1 p-1.5 sm:px-3 sm:py-1.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs sm:text-sm font-medium border border-slate-700 transition cursor-pointer"
            title="Менің файлдарым"
          >
            <FolderOpen className="w-4 h-4 text-sky-400" />
            <span className="hidden md:inline">Менің файлдарым</span>
            {presentationCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-slate-700 text-slate-300 text-[10px] sm:text-xs font-mono font-bold">
                {presentationCount}
              </span>
            )}
          </button>

          {/* Help Button */}
          <button
            onClick={onOpenHelp}
            className="p-1.5 sm:p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition cursor-pointer"
            title="Көмек және нұсқаулық"
          >
            <HelpCircle className="w-4 h-4" />
          </button>

          {/* Language Switcher: single compact button on mobile, 3-button segmented control on sm+ */}
          <button
            onClick={() => {
              const order: AppLanguage[] = ['kk', 'ru', 'en'];
              const next = order[(order.indexOf(currentLang) + 1) % order.length];
              onSelectLang(next);
            }}
            className="sm:hidden px-2 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[11px] font-bold uppercase text-sky-400 transition cursor-pointer"
            title="Тілді ауыстыру"
          >
            {currentLang}
          </button>

          <div className="hidden sm:flex items-center bg-slate-800 rounded-xl p-0.5 border border-slate-700 text-xs">
            {(['kk', 'ru', 'en'] as AppLanguage[]).map((lang) => (
              <button
                key={lang}
                onClick={() => onSelectLang(lang)}
                className={`px-2 py-1 rounded-lg uppercase font-medium transition cursor-pointer ${
                  currentLang === lang
                    ? 'bg-sky-600 text-white shadow-xs font-bold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {lang}
              </button>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
};
