import React, { useState } from 'react';
import {
  Sparkles,
  ArrowRight,
  SlidersHorizontal,
  Palette,
  Layers,
  ChevronDown,
  Loader2,
  Zap,
} from 'lucide-react';
import { THEMES_REGISTRY, THEMES_LIST, detectBestThemeForTopic } from '../designs/registry';

interface PromptBarProps {
  onGenerate: (params: {
    topic: string;
    slide_count: number;
    design_id?: string;
  }) => Promise<void>;
  isGenerating: boolean;
  onOpenThemesGallery: () => void;
}

export const PromptBar: React.FC<PromptBarProps> = ({
  onGenerate,
  isGenerating,
  onOpenThemesGallery,
}) => {
  const [topic, setTopic] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [slideCount, setSlideCount] = useState<number>(15);
  const [selectedThemeId, setSelectedThemeId] = useState<string>('');

  const quickPresets = [
    { label: '🤖 Жасанды интеллект', topic: 'Жасанды интеллекттің дамуы мен болашағы' },
    { label: '👥 Абай мен Шәкәрім', topic: 'Абай мен Шәкәрім: Рухани сабақтастық пен өмірбаяны' },
    { label: '🏛️ Қазақстан тарихы', topic: 'Қазақстан тарихының ұлы белестері' },
    { label: '🚀 Стартап питч', topic: 'SaaS платформасының инвестициялық питч-дегі' },
    { label: '🌿 Жасыл энергетика', topic: 'Жасыл экономика және экологиялық бастамалар' },
    { label: '🧠 Адам миының құпиясы', topic: 'Адам миы қалай жұмыс істейді және когнитивті ғылым' },
  ];

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!topic.trim() || isGenerating) return;

    onGenerate({
      topic: topic.trim(),
      slide_count: slideCount,
      design_id: selectedThemeId || undefined,
    });
  };

  const autoDetectedTheme = topic.trim() ? detectBestThemeForTopic(topic) : null;

  return (
    <div className="w-full max-w-4xl mx-auto px-3.5 sm:px-4 py-6 sm:py-12">
      {/* Hero Badge */}
      <div className="text-center mb-5 sm:mb-6 space-y-2.5 sm:space-y-3">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 text-[11px] sm:text-xs font-semibold shadow-xs">
          <Sparkles className="w-3.5 h-3.5 text-sky-400 shrink-0" />
          <span>PRO VERSION • AI PRESENTATION PLATFORM</span>
        </div>
        <h1 className="text-2xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight px-1">
          Бір сөзбен <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-teal-300 to-indigo-400">кәсіби презентация</span> жасаңыз
        </h1>
        <p className="text-slate-400 text-xs sm:text-base max-w-2xl mx-auto leading-relaxed px-1">
          Артық сұрақтарсыз — тақырыпты жазыңыз. AI мазмұнын жоспарлайды, 30 дизайнның ішінен сәйкесін таңдайды және 16:9 PPTX файлын дайындайды.
        </p>
      </div>

      {/* Main Single-Input Box */}
      <form
        onSubmit={handleSubmit}
        className="bg-slate-850/90 border border-slate-700/80 rounded-2xl sm:rounded-3xl p-2.5 sm:p-3 shadow-2xl backdrop-blur-md transition-all focus-within:border-sky-500/80 focus-within:ring-4 focus-within:ring-sky-500/10 mb-5"
      >
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <div className="flex-1 relative flex items-center min-w-0">
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Тақырып: Жасанды интеллект, Қазақстан тарихы..."
              className="w-full bg-transparent px-3 sm:px-4 py-3 sm:py-3.5 text-sm sm:text-lg text-white placeholder-slate-500 focus:outline-none"
              autoFocus
              disabled={isGenerating}
            />
          </div>

          <div className="flex items-center gap-2 justify-between sm:justify-end pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-800">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`px-3 py-2.5 sm:p-3 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer ${
                showAdvanced || selectedThemeId
                  ? 'bg-slate-750 text-sky-300 border-sky-500/40'
                  : 'bg-slate-800/80 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border-slate-700'
              }`}
              title="Параметрлерді баптау"
            >
              <SlidersHorizontal className="w-4 h-4 shrink-0" />
              <span>Баптаулар</span>
            </button>

            <button
              type="submit"
              disabled={!topic.trim() || isGenerating}
              className="flex-1 sm:flex-initial px-5 sm:px-6 py-2.5 sm:py-3.5 rounded-xl sm:rounded-2xl bg-gradient-to-r from-sky-500 via-sky-600 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-sm sm:text-base shadow-lg shadow-sky-500/20 transition-all flex items-center justify-center gap-2 cursor-pointer shrink-0"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
                  <span>Жасалуда...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  <span>Жасау</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Auto-detected theme chip */}
        {autoDetectedTheme && !selectedThemeId && (
          <div className="px-3 sm:px-4 py-2 mt-2 pt-2 border-t border-slate-850/80 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
              <span className="shrink-0">AI дизайн:</span>
              <span className="font-semibold text-sky-300 truncate">
                {autoDetectedTheme.nameKz}
              </span>
            </div>
            <button
              type="button"
              onClick={onOpenThemesGallery}
              className="text-sky-400 hover:text-sky-300 underline font-medium cursor-pointer shrink-0"
            >
              Өзгерту
            </button>
          </div>
        )}

        {/* Advanced Panel */}
        {showAdvanced && (
          <div className="mt-3 pt-3 border-t border-slate-800 px-3 pb-2 grid grid-cols-1 sm:grid-cols-2 gap-4 animate-fade-in text-xs">
            {/* Slide count */}
            <div>
              <label className="block text-slate-400 font-medium mb-1.5 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-sky-400" />
                <span>Слайд саны:</span>
              </label>
              <div className="grid grid-cols-4 gap-1.5">
                {[5, 10, 15, 20].map((count) => (
                  <button
                    key={count}
                    type="button"
                    onClick={() => setSlideCount(count)}
                    className={`py-1.5 rounded-lg border font-semibold transition cursor-pointer text-center ${
                      slideCount === count
                        ? 'bg-sky-600 text-white border-sky-500'
                        : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
                    }`}
                  >
                    {count}
                  </button>
                ))}
              </div>
            </div>

            {/* Force theme */}
            <div>
              <label className="block text-slate-400 font-medium mb-1.5 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Palette className="w-3.5 h-3.5 text-sky-400" />
                  <span>Дизайн таңдау:</span>
                </span>
                <button
                  type="button"
                  onClick={onOpenThemesGallery}
                  className="text-sky-400 hover:text-sky-300 underline cursor-pointer"
                >
                  Барлық 30 шаблон
                </button>
              </label>

              <select
                value={selectedThemeId}
                onChange={(e) => setSelectedThemeId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-white text-xs focus:outline-none focus:border-sky-500"
              >
                <option value="">Автоматты (AI тақырыпқа сай таңдайды)</option>
                {THEMES_LIST.map((th) => (
                  <option key={th.id} value={th.id}>
                    {th.nameKz} ({th.name})
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </form>

      {/* Popular Presets Chips */}
      <div>
        <p className="text-xs text-slate-400 uppercase font-semibold tracking-wider mb-2.5 text-center">
          💡 Бір шертумен бастау / Quick Prompts:
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2">
          {quickPresets.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => {
                setTopic(preset.topic);
                onGenerate({
                  topic: preset.topic,
                  slide_count: 15,
                });
              }}
              className="text-xs px-3.5 py-2 rounded-xl bg-slate-850 hover:bg-slate-800 border border-slate-750 hover:border-sky-500/40 text-slate-300 hover:text-white transition shadow-xs cursor-pointer flex items-center gap-1.5"
            >
              <span>{preset.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
