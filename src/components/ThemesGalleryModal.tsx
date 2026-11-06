import React, { useState } from 'react';
import { X, Palette, Check, Sparkles, Filter } from 'lucide-react';
import { THEMES_LIST } from '../designs/registry';
import { ThemeConfig } from '../designs/types';

interface ThemesGalleryModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeThemeId: string;
  onSelectTheme: (themeId: string) => void;
}

export const ThemesGalleryModal: React.FC<ThemesGalleryModalProps> = ({
  isOpen,
  onClose,
  activeThemeId,
  onSelectTheme,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');

  if (!isOpen) return null;

  const categories = ['All', 'Minimal', 'Modern', 'Tech', 'Editorial', 'Corporate', 'Creative', 'Academic'];

  const filteredThemes = THEMES_LIST.filter((theme) => {
    const matchesCat = selectedCategory === 'All' || theme.category === selectedCategory;
    const matchesSearch =
      searchQuery === '' ||
      theme.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      theme.nameKz.toLowerCase().includes(searchQuery.toLowerCase()) ||
      theme.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2.5 sm:p-6 bg-slate-950/85 backdrop-blur-md animate-fade-in">
      <div className="bg-slate-900 border border-slate-750 w-full max-w-5xl rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 sm:p-6 border-b border-slate-800 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl sm:rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 text-white flex items-center justify-center shadow-md shrink-0">
              <Palette className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base sm:text-xl font-bold text-white truncate">30 Кәсіби Дизайн</h2>
                <span className="text-[11px] sm:text-xs px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-400 font-semibold border border-sky-500/30 shrink-0">
                  {THEMES_LIST.length} стиль
                </span>
              </div>
              <p className="text-[11px] sm:text-xs text-slate-400 mt-0.5 line-clamp-1">
                Әр шаблон жеке дизайн жүйесі, палитрасы және композициясымен жасалған
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filters */}
        <div className="px-4 sm:px-6 py-2.5 sm:py-3 border-b border-slate-800/80 bg-slate-850/60 flex flex-wrap items-center justify-between gap-2.5">
          <div className="w-full sm:w-auto max-w-full flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition cursor-pointer whitespace-nowrap shrink-0 ${
                  selectedCategory === cat
                    ? 'bg-sky-600 text-white shadow-sm'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="w-full sm:w-64">
            <input
              type="text"
              placeholder="Дизайн іздеу..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
          </div>
        </div>

        {/* Themes Grid */}
        <div className="p-4 sm:p-6 overflow-y-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 sm:gap-4 flex-1">
          {filteredThemes.map((theme) => {
            const isSelected = activeThemeId === theme.id;
            return (
              <div
                key={theme.id}
                onClick={() => {
                  onSelectTheme(theme.id);
                  onClose();
                }}
                className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between group relative overflow-hidden ${
                  isSelected
                    ? 'bg-sky-950/40 border-sky-500 ring-2 ring-sky-500/30 shadow-lg'
                    : 'bg-slate-850 hover:bg-slate-800/90 border-slate-750 hover:border-slate-600'
                }`}
              >
                <div>
                  {/* Theme Preview Card Graphic */}
                  <div
                    className="w-full h-24 rounded-xl p-3 mb-3 flex flex-col justify-between relative overflow-hidden border border-black/10 shadow-inner"
                    style={{
                      backgroundColor: `#${theme.bgColor}`,
                      color: `#${theme.textColor}`,
                    }}
                  >
                    <div className="flex justify-between items-center text-[10px] font-mono opacity-60">
                      <span>16:9 SLIDE</span>
                      <span className="uppercase">{theme.category}</span>
                    </div>

                    <div>
                      <div
                        className="text-xs font-bold leading-tight truncate"
                        style={{ color: `#${theme.primaryColor}` }}
                      >
                        {theme.nameKz}
                      </div>
                      <div
                        className="w-8 h-0.5 rounded-full mt-1.5"
                        style={{ backgroundColor: `#${theme.accentColor}` }}
                      />
                    </div>

                    <div className="flex gap-1.5 mt-1">
                      <div
                        className="w-3.5 h-3.5 rounded-full border border-black/20"
                        style={{ backgroundColor: `#${theme.primaryColor}` }}
                        title="Primary"
                      />
                      <div
                        className="w-3.5 h-3.5 rounded-full border border-black/20"
                        style={{ backgroundColor: `#${theme.secondaryColor}` }}
                        title="Secondary"
                      />
                      <div
                        className="w-3.5 h-3.5 rounded-full border border-black/20"
                        style={{ backgroundColor: `#${theme.accentColor}` }}
                        title="Accent"
                      />
                      <div
                        className="w-3.5 h-3.5 rounded-full border border-black/20"
                        style={{ backgroundColor: `#${theme.cardBg}` }}
                        title="Card Surface"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-1 mb-1">
                    <h3 className="font-bold text-white text-sm group-hover:text-sky-300 transition">
                      {theme.name}
                    </h3>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-medium">
                      {theme.category}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-3">
                    {theme.description}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                  <span className="text-slate-400 text-[11px] truncate max-w-[70%]">
                    💡 {theme.recommendedTopics.slice(0, 2).join(', ')}
                  </span>
                  {isSelected ? (
                    <span className="text-sky-400 font-bold flex items-center gap-1 text-[11px]">
                      <Check className="w-3.5 h-3.5" />
                      Таңдалған
                    </span>
                  ) : (
                    <span className="text-slate-400 group-hover:text-white transition text-[11px]">
                      Қолдану →
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
