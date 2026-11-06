import React from 'react';
import { X, FolderOpen, Calendar, Layers, Download, Trash2, ArrowRight, Award, Palette } from 'lucide-react';
import { PresentationData, AppLanguage } from '../designs/types';
import { THEMES_REGISTRY } from '../designs/registry';
import { exportPresentationToPPTX } from '../services/api';

interface MyPresentationsModalProps {
  isOpen: boolean;
  onClose: () => void;
  presentations: PresentationData[];
  onSelectPresentation: (pres: PresentationData) => void;
  onDeletePresentation: (id: string) => void;
  currentLang: AppLanguage;
}

export const MyPresentationsModal: React.FC<MyPresentationsModalProps> = ({
  isOpen,
  onClose,
  presentations,
  onSelectPresentation,
  onDeletePresentation,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-750 w-full max-w-2xl rounded-3xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-sky-500/20 text-sky-400 flex items-center justify-center">
              <FolderOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Менің презентацияларым</h2>
              <p className="text-xs text-slate-400">Сақталған барлық презентациялар жинағы</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* List */}
        <div className="p-5 overflow-y-auto space-y-3 flex-1">
          {presentations.length === 0 ? (
            <div className="text-center py-12 text-slate-400 space-y-2">
              <FolderOpen className="w-12 h-12 mx-auto text-slate-600 mb-2" />
              <p className="text-sm">Әзірге сақталған презентациялар жоқ.</p>
              <p className="text-xs text-slate-500">Кез келген тақырыпты жазып, жаңасын жасап көріңіз!</p>
            </div>
          ) : (
            presentations.map((item) => {
              const theme = THEMES_REGISTRY[item.design_id] || THEMES_REGISTRY.swiss_minimalism;
              return (
                <div
                  key={item.id}
                  className="bg-slate-850 hover:bg-slate-800/90 border border-slate-750 rounded-2xl p-4 transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 group"
                >
                  <div
                    className="flex-1 cursor-pointer"
                    onClick={() => {
                      onSelectPresentation(item);
                      onClose();
                    }}
                  >
                    <h3 className="font-bold text-white text-base group-hover:text-sky-300 transition line-clamp-1">
                      {item.title_presentation || item.topic}
                    </h3>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-1.5 flex-wrap">
                      <span className="flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5 text-sky-400" />
                        {item.slides?.length || item.slide_count} слайд
                      </span>
                      <span className="flex items-center gap-1 text-slate-300">
                        <Palette className="w-3 h-3 text-amber-400" />
                        {theme.nameKz}
                      </span>
                      <span className="flex items-center gap-1 text-emerald-400 font-mono font-semibold">
                        <Award className="w-3 h-3" />
                        {item.quality_score?.total || 96} Score
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {new Date(item.createdAt).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <button
                      onClick={() => exportPresentationToPPTX(item)}
                      title="PPTX жүктеу"
                      className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-emerald-400 border border-slate-700 transition cursor-pointer"
                    >
                      <Download className="w-4 h-4" />
                    </button>

                    <button
                      onClick={() => onDeletePresentation(item.id)}
                      className="p-2.5 rounded-xl bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 border border-slate-700 transition cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>

                    <button
                      onClick={() => {
                        onSelectPresentation(item);
                        onClose();
                      }}
                      className="flex items-center gap-1 px-3.5 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold transition cursor-pointer"
                    >
                      <span>Ашу</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
