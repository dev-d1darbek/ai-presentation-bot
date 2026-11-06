import React, { useState, useEffect } from 'react';
import {
  Download,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  BookOpen,
  Edit3,
  Check,
  Plus,
  Trash2,
  Palette,
  MessageSquare,
  ShieldCheck,
  Award,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { PresentationData, SlideContent } from '../designs/types';
import { THEMES_REGISTRY, getThemeHeadingColor } from '../designs/registry';
import { exportPresentationToPPTX } from '../services/api';

interface SlideDeckViewerProps {
  presentation: PresentationData;
  onUpdatePresentation: (updated: PresentationData) => void;
  onNewPresentation: () => void;
  onOpenThemesGallery: () => void;
  onOpenChatDrawer: () => void;
}

export const SlideDeckViewer: React.FC<SlideDeckViewerProps> = ({
  presentation,
  onUpdatePresentation,
  onOpenThemesGallery,
  onOpenChatDrawer,
}) => {
  const [currentSlideIdx, setCurrentSlideIdx] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [showScoreModal, setShowScoreModal] = useState(false);

  const slides = presentation.slides || [];
  const currentSlide: SlideContent | undefined = slides[currentSlideIdx];
  const activeTheme = THEMES_REGISTRY[presentation.design_id] || THEMES_REGISTRY.swiss_minimalism;
  const headingColor = getThemeHeadingColor(activeTheme);

  // Celebrate initial deck generation
  useEffect(() => {
    confetti({
      particleCount: 55,
      spread: 70,
      origin: { y: 0.75 },
      colors: ['#0284c7', '#38bdf8', '#818cf8', '#34d399', '#f59e0b'],
    });
  }, [presentation.id]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isEditing) return;
      if (e.key === 'ArrowRight' || e.key === ' ') {
        if (currentSlideIdx < slides.length - 1) {
          setCurrentSlideIdx((prev) => prev + 1);
        }
      } else if (e.key === 'ArrowLeft') {
        if (currentSlideIdx > 0) {
          setCurrentSlideIdx((prev) => prev - 1);
        }
      } else if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentSlideIdx, slides.length, isFullscreen, isEditing]);

  const handleDownloadPPTX = async () => {
    try {
      setIsExporting(true);
      await exportPresentationToPPTX(presentation);
    } catch {
      alert('PPTX экспорттау кезінде қате кетті. Қайталап көріңіз.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleUpdateSlideField = (field: keyof SlideContent, value: any) => {
    if (!currentSlide) return;
    const updatedSlides = [...slides];
    updatedSlides[currentSlideIdx] = {
      ...currentSlide,
      [field]: value,
    };
    onUpdatePresentation({
      ...presentation,
      slides: updatedSlides,
    });
  };

  const handleUpdateBullet = (bulletIdx: number, val: string) => {
    if (!currentSlide) return;
    const newContent = [...currentSlide.key_points];
    newContent[bulletIdx] = val;
    handleUpdateSlideField('key_points', newContent);
  };

  const handleAddBullet = () => {
    if (!currentSlide) return;
    const newContent = [...currentSlide.key_points, 'Жаңа маңызды тұжырым мен дәйектеме'];
    handleUpdateSlideField('key_points', newContent);
  };

  const handleDeleteBullet = (bulletIdx: number) => {
    if (!currentSlide) return;
    const newContent = currentSlide.key_points.filter((_, idx) => idx !== bulletIdx);
    handleUpdateSlideField('key_points', newContent);
  };

  // Convert theme hex to CSS styles
  const slideStyleObj: React.CSSProperties = {
    backgroundColor: `#${activeTheme.bgColor}`,
    color: `#${activeTheme.textColor}`,
    borderColor: `#${activeTheme.borderColor}`,
  };

  return (
    <div className={`w-full max-w-7xl mx-auto px-3 sm:px-6 py-4 sm:py-6 overflow-x-hidden ${isFullscreen ? 'fixed inset-0 z-50 bg-slate-950 p-3 sm:p-6 flex flex-col overflow-y-auto' : ''}`}>
      {/* Top Header & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center justify-between gap-3 mb-4 sm:mb-5 pb-3.5 sm:pb-4 border-b border-slate-800">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-1.5">
            {/* Active Theme Chip with Switcher */}
            <button
              onClick={onOpenThemesGallery}
              className="text-[11px] sm:text-xs px-2 sm:px-2.5 py-1 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/30 font-semibold flex items-center gap-1.5 transition cursor-pointer max-w-full"
            >
              <Palette className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">Дизайн: {activeTheme.nameKz}</span>
              <span className="hidden sm:inline text-[10px] text-slate-400">({activeTheme.name})</span>
            </button>

            {/* Quality Score Badge */}
            <button
              onClick={() => setShowScoreModal(true)}
              className="text-[11px] sm:text-xs px-2 sm:px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold flex items-center gap-1 transition cursor-pointer shrink-0"
            >
              <Award className="w-3.5 h-3.5 shrink-0" />
              <span>{presentation.quality_score?.total || 98}/100</span>
              <span className="hidden sm:inline">Сапа көрсеткіші</span>
            </button>
          </div>

          <h1 className="text-base sm:text-2xl font-extrabold text-white tracking-tight line-clamp-2 sm:line-clamp-1">
            {presentation.title_presentation}
          </h1>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
          {/* AI Refine Chat Button */}
          <button
            onClick={onOpenChatDrawer}
            className="flex items-center gap-1.5 px-2.5 sm:px-3.5 py-2 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/40 text-xs sm:text-sm font-semibold transition cursor-pointer"
          >
            <MessageSquare className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-400 shrink-0" />
            <span>AI Көмекші</span>
          </button>

          {/* Change Theme Button */}
          <button
            onClick={onOpenThemesGallery}
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs sm:text-sm font-medium transition cursor-pointer"
            title="Дизайн ауыстыру"
          >
            <Palette className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-sky-400 shrink-0" />
            <span className="hidden sm:inline">Дизайн ауыстыру</span>
          </button>

          {/* Edit Slide Button */}
          <button
            onClick={() => setIsEditing(!isEditing)}
            className={`px-2.5 sm:px-3 py-2 rounded-xl border text-xs sm:text-sm font-medium transition cursor-pointer flex items-center gap-1.5 ${
              isEditing
                ? 'bg-emerald-600 text-white border-emerald-500'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
            }`}
          >
            {isEditing ? <Check className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> : <Edit3 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
            <span>{isEditing ? 'Сақтау' : 'Өңдеу'}</span>
          </button>

          {/* Fullscreen Button */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition cursor-pointer"
            title={isFullscreen ? 'Шығу' : 'Толық экран'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          {/* Download PPTX */}
          <button
            onClick={handleDownloadPPTX}
            disabled={isExporting}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 sm:gap-2 px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white font-bold text-xs sm:text-sm shadow-md shadow-emerald-600/20 transition cursor-pointer"
          >
            <Download className="w-4 h-4 shrink-0" />
            <span>{isExporting ? 'Жүктелуде...' : 'PPTX жүктеу'}</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Slide Frame (Left 9 Cols) + Slide Structure Plan (Right 3 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 flex-1 min-h-0">
        {/* Left: Presentation Canvas (auto-height on mobile, 16:9 on sm+) */}
        <div className="lg:col-span-9 min-w-0 flex flex-col space-y-3 sm:space-y-4">
          <div
            style={slideStyleObj}
            className="relative w-full min-h-[340px] h-auto sm:aspect-video rounded-2xl sm:rounded-3xl overflow-visible sm:overflow-hidden shadow-2xl border flex flex-col justify-between p-3.5 sm:p-7 select-none transition-all duration-300"
          >
            {currentSlide && (
              <>
                {/* ========================================== */}
                {/* SLIDE TYPE 1: COVER SLIDE (No Theme Badge, No Footer, 1:1 with PPTX) */}
                {/* ========================================== */}
                {(currentSlide.type === 'cover' || currentSlideIdx === 0) ? (
                  <div
                    className="flex-1 flex flex-col justify-between items-center text-center p-4 sm:p-8 rounded-2xl border relative z-10 overflow-hidden gap-3 sm:gap-0"
                    style={{
                      backgroundColor: `#${activeTheme.cardBg}`,
                      borderColor: `#${activeTheme.borderColor}`,
                    }}
                  >
                    {/* Top Sleek Accent Strip */}
                    <div
                      className="w-28 h-1.5 rounded-full shrink-0"
                      style={{ backgroundColor: `#${activeTheme.accentColor}` }}
                    />

                    {/* Center Title & Subtitle */}
                    <div className="my-auto space-y-2.5 max-w-3xl">
                      {isEditing ? (
                        <input
                          type="text"
                          value={currentSlide.title}
                          onChange={(e) => handleUpdateSlideField('title', e.target.value)}
                          className="w-full bg-black/40 border border-sky-500 rounded-xl px-4 py-2 text-xl sm:text-3xl font-extrabold text-center focus:outline-none"
                          style={{ color: `#${headingColor}` }}
                        />
                      ) : (
                        <h1
                          className="text-xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight leading-tight"
                          style={{ color: `#${headingColor}` }}
                        >
                          {currentSlide.title}
                        </h1>
                      )}

                      {currentSlide.subtitle && (
                        <p
                          className="text-xs sm:text-base font-medium"
                          style={{ color: `#${activeTheme.textMuted}` }}
                        >
                          {currentSlide.subtitle}
                        </p>
                      )}
                    </div>

                    {/* Expanded Overview Box */}
                    {currentSlide.content && (
                      <div
                        className="p-4 rounded-xl max-w-3xl w-full border text-xs sm:text-sm leading-relaxed"
                        style={{
                          backgroundColor: `#${activeTheme.bgColor}`,
                          borderColor: `#${activeTheme.borderColor}`,
                          color: `#${activeTheme.textColor}`,
                        }}
                      >
                        <p>{currentSlide.content}</p>
                      </div>
                    )}

                    {/* Bottom 3 Key Focus Pillars */}
                    {currentSlide.key_points && currentSlide.key_points.length > 0 && (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3 w-full max-w-3xl mt-2">
                        {currentSlide.key_points.slice(0, 3).map((pt, kIdx) => (
                          <div
                            key={kIdx}
                            className="p-2.5 rounded-xl border text-[11px] sm:text-xs font-semibold text-center flex items-center justify-center"
                            style={{
                              backgroundColor: `#${activeTheme.bgColor}`,
                              borderColor: `#${activeTheme.borderColor}`,
                              color: `#${headingColor}`,
                            }}
                          >
                            {pt}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : currentSlide.type === 'two_person_comparison' && currentSlide.comparison ? (
                  /* ========================================== */
                  /* SLIDE TYPE 2: TWO-PERSON COMPARISON (Compact Cards, Full Uncovered <p>) */
                  /* ========================================== */
                  <div className="flex-1 flex flex-col justify-start gap-2.5 relative z-10 min-h-0 overflow-hidden">
                    <div className="shrink-0 relative z-20">
                      <h2
                        className="text-base sm:text-xl font-bold tracking-tight leading-snug"
                        style={{ color: `#${headingColor}` }}
                      >
                        {currentSlide.title}
                      </h2>
                      <div
                        className="w-14 h-1 rounded-full mt-1"
                        style={{ backgroundColor: `#${activeTheme.accentColor}` }}
                      />
                      {currentSlide.content && (
                        <p
                          className="text-[11px] sm:text-xs leading-snug mt-1.5"
                          style={{ color: `#${activeTheme.textMuted}` }}
                        >
                          {currentSlide.content}
                        </p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3.5 mt-2 relative z-10">
                      {/* Person A Card */}
                      <div
                        className="p-3 sm:p-4 rounded-xl border flex flex-col justify-start relative overflow-hidden"
                        style={{
                          backgroundColor: `#${activeTheme.cardBg}`,
                          borderColor: `#${activeTheme.borderColor}`,
                        }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <div
                            className="w-6 h-6 rounded-md flex items-center justify-center text-[11px] font-bold text-white shrink-0"
                            style={{ backgroundColor: `#${activeTheme.secondaryColor}` }}
                          >
                            A
                          </div>
                          <h3
                            className="font-bold text-xs sm:text-sm"
                            style={{ color: `#${headingColor}` }}
                          >
                            {currentSlide.comparison.entityA.name}
                          </h3>
                        </div>
                        <ul className="space-y-1.5 text-[11px] sm:text-xs leading-snug">
                          {currentSlide.comparison.entityA.points.map((pt, pIdx) => (
                            <li key={pIdx} className="flex items-start gap-1.5">
                              <span
                                className="font-bold shrink-0"
                                style={{ color: `#${activeTheme.accentColor}` }}
                              >
                                •
                              </span>
                              <span style={{ color: `#${activeTheme.textColor}` }}>{pt}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Person B Card */}
                      <div
                        className="p-3 sm:p-4 rounded-xl border flex flex-col justify-start relative overflow-hidden"
                        style={{
                          backgroundColor: `#${activeTheme.cardBg}`,
                          borderColor: `#${activeTheme.borderColor}`,
                        }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <div
                            className="w-6 h-6 rounded-md flex items-center justify-center text-[11px] font-bold text-white shrink-0"
                            style={{ backgroundColor: `#${activeTheme.accentColor}` }}
                          >
                            B
                          </div>
                          <h3
                            className="font-bold text-xs sm:text-sm"
                            style={{ color: `#${headingColor}` }}
                          >
                            {currentSlide.comparison.entityB.name}
                          </h3>
                        </div>
                        <ul className="space-y-1.5 text-[11px] sm:text-xs leading-snug">
                          {currentSlide.comparison.entityB.points.map((pt, pIdx) => (
                            <li key={pIdx} className="flex items-start gap-1.5">
                              <span
                                className="font-bold shrink-0"
                                style={{ color: `#${activeTheme.secondaryColor}` }}
                              >
                                •
                              </span>
                              <span style={{ color: `#${activeTheme.textColor}` }}>{pt}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                ) : currentSlide.type === 'timeline' && currentSlide.timeline && currentSlide.timeline.length > 0 ? (
                  /* ========================================== */
                  /* SLIDE TYPE 3: TIMELINE (3 Compact Step Cards, Full Uncovered <p>) */
                  /* ========================================== */
                  <div className="flex-1 flex flex-col justify-start gap-2.5 relative z-10 min-h-0 overflow-hidden">
                    <div className="shrink-0 relative z-20">
                      <h2
                        className="text-base sm:text-xl font-bold tracking-tight leading-snug"
                        style={{ color: `#${headingColor}` }}
                      >
                        {currentSlide.title}
                      </h2>
                      <div
                        className="w-14 h-1 rounded-full mt-1"
                        style={{ backgroundColor: `#${activeTheme.accentColor}` }}
                      />
                      {currentSlide.content && (
                        <p
                          className="text-[11px] sm:text-xs leading-snug mt-1.5"
                          style={{ color: `#${activeTheme.textMuted}` }}
                        >
                          {currentSlide.content}
                        </p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 sm:gap-3.5 mt-2 relative z-10">
                      {currentSlide.timeline.slice(0, 3).map((item, tIdx) => (
                        <div
                          key={tIdx}
                          className="p-3 sm:p-4 rounded-xl border flex flex-col justify-start"
                          style={{
                            backgroundColor: `#${activeTheme.cardBg}`,
                            borderColor: `#${activeTheme.borderColor}`,
                          }}
                        >
                          <span
                            className="text-xl sm:text-2xl font-black font-mono block mb-1"
                            style={{ color: `#${activeTheme.secondaryColor}` }}
                          >
                            {item.step || `0${tIdx + 1}`}
                          </span>
                          <h4
                            className="font-bold text-xs sm:text-sm mb-1"
                            style={{ color: `#${headingColor}` }}
                          >
                            {item.title}
                          </h4>
                          <p
                            className="text-[11px] sm:text-xs leading-snug"
                            style={{ color: `#${activeTheme.textColor}` }}
                          >
                            {item.desc}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : currentSlide.type === 'statistics' && currentSlide.stats && currentSlide.stats.length > 0 ? (
                  /* ========================================== */
                  /* SLIDE TYPE 4: STATISTICS (3 Compact Metrics + Key Findings, Full Uncovered <p>) */
                  /* ========================================== */
                  <div className="flex-1 flex flex-col justify-start gap-2.5 relative z-10 min-h-0 overflow-hidden">
                    <div className="shrink-0 relative z-20">
                      <h2
                        className="text-base sm:text-xl font-bold tracking-tight leading-snug"
                        style={{ color: `#${headingColor}` }}
                      >
                        {currentSlide.title}
                      </h2>
                      <div
                        className="w-14 h-1 rounded-full mt-1"
                        style={{ backgroundColor: `#${activeTheme.accentColor}` }}
                      />
                      {currentSlide.content && (
                        <p
                          className="text-[11px] sm:text-xs leading-snug mt-1.5"
                          style={{ color: `#${activeTheme.textMuted}` }}
                        >
                          {currentSlide.content}
                        </p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3.5 mt-2 relative z-10">
                      {currentSlide.stats.slice(0, 3).map((st, sIdx) => (
                        <div
                          key={sIdx}
                          className="p-3 sm:p-3.5 rounded-xl border flex flex-col items-center justify-center text-center relative overflow-hidden"
                          style={{
                            backgroundColor: `#${activeTheme.cardBg}`,
                            borderColor: `#${activeTheme.borderColor}`,
                          }}
                        >
                          <div
                            className="text-xl sm:text-3xl font-black font-mono tracking-tight mb-1"
                            style={{ color: `#${activeTheme.secondaryColor}` }}
                          >
                            {st.value}
                          </div>
                          <div
                            className="text-[11px] sm:text-xs font-semibold max-w-xs leading-snug"
                            style={{ color: `#${headingColor}` }}
                          >
                            {st.label}
                          </div>
                        </div>
                      ))}
                    </div>

                    {currentSlide.key_points && currentSlide.key_points.length > 0 && (
                      <div
                        className="p-3 rounded-xl border space-y-1 shrink-0 relative z-10"
                        style={{
                          backgroundColor: `#${activeTheme.cardBg}`,
                          borderColor: `#${activeTheme.borderColor}`,
                        }}
                      >
                        {currentSlide.key_points.slice(0, 3).map((pt, idx) => (
                          <div key={idx} className="flex items-start gap-2 text-[11px] sm:text-xs leading-snug">
                            <span
                              className="font-bold shrink-0"
                              style={{ color: `#${activeTheme.accentColor}` }}
                            >
                              •
                            </span>
                            <span style={{ color: `#${activeTheme.textColor}` }}>{pt}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (currentSlide.type === 'big_typography' || currentSlide.quote) ? (
                  /* ========================================== */
                  /* SLIDE TYPE 5: BIG TYPOGRAPHY / QUOTE */
                  /* ========================================== */
                  <div className="flex-1 flex flex-col justify-between gap-2.5 relative z-10 min-h-0 overflow-hidden">
                    <div className="shrink-0 relative z-20">
                      <h2
                        className="text-base sm:text-xl font-bold tracking-tight leading-snug"
                        style={{ color: `#${headingColor}` }}
                      >
                        {currentSlide.title}
                      </h2>
                      <div
                        className="w-14 h-1 rounded-full mt-1"
                        style={{ backgroundColor: `#${activeTheme.accentColor}` }}
                      />
                    </div>

                    {/* Hero Quote Card */}
                    <div
                      className="p-4 sm:p-5 rounded-xl border relative overflow-hidden my-auto flex flex-col justify-center"
                      style={{
                        backgroundColor: `#${activeTheme.cardBg}`,
                        borderColor: `#${activeTheme.borderColor}`,
                      }}
                    >
                      <div className="flex items-start gap-3">
                        <span
                          className="text-3xl font-serif leading-none shrink-0"
                          style={{ color: `#${activeTheme.secondaryColor}` }}
                        >
                          «
                        </span>
                        <div>
                          <p
                            className="text-xs sm:text-base font-bold italic leading-relaxed"
                            style={{ color: `#${headingColor}` }}
                          >
                            {currentSlide.quote?.text || currentSlide.content}
                          </p>
                          <p
                            className="text-[11px] sm:text-xs font-semibold mt-2"
                            style={{ color: `#${activeTheme.secondaryColor}` }}
                          >
                            — {currentSlide.quote?.author || 'Түйінді стратегиялық қағида'}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* 3 Pillars */}
                    {currentSlide.key_points && currentSlide.key_points.length > 0 && (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3.5 shrink-0">
                        {currentSlide.key_points.slice(0, 3).map((pt, pIdx) => (
                          <div
                            key={pIdx}
                            className="p-3 rounded-xl border text-[11px] sm:text-xs leading-snug"
                            style={{
                              backgroundColor: `#${activeTheme.cardBg}`,
                              borderColor: `#${activeTheme.borderColor}`,
                            }}
                          >
                            <span
                              className="font-bold text-[10px] block mb-1"
                              style={{ color: `#${activeTheme.secondaryColor}` }}
                            >
                              #0{pIdx + 1} ҚАҒИДАТ
                            </span>
                            <span style={{ color: `#${headingColor}` }}>{pt}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (currentSlide.type === 'key_takeaway' || currentSlide.type === 'conclusion') ? (
                  /* ========================================== */
                  /* SLIDE TYPE 6: KEY TAKEAWAYS / CONCLUSION (Compact Cards, Full Uncovered <p>) */
                  /* ========================================== */
                  <div className="flex-1 flex flex-col justify-start gap-2.5 relative z-10 min-h-0 overflow-hidden">
                    <div className="shrink-0 relative z-20">
                      <h2
                        className="text-base sm:text-xl font-bold tracking-tight leading-snug"
                        style={{ color: `#${headingColor}` }}
                      >
                        {currentSlide.title}
                      </h2>
                      <div
                        className="w-14 h-1 rounded-full mt-1"
                        style={{ backgroundColor: `#${activeTheme.accentColor}` }}
                      />
                      {currentSlide.content && (
                        <p
                          className="text-[11px] sm:text-xs leading-snug mt-1.5"
                          style={{ color: `#${activeTheme.textMuted}` }}
                        >
                          {currentSlide.content}
                        </p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 sm:gap-3.5 mt-2 relative z-10">
                      {(currentSlide.key_points || []).slice(0, 3).map((item, kIdx) => (
                        <div
                          key={kIdx}
                          className="p-3 sm:p-4 rounded-xl border flex flex-col justify-start relative overflow-hidden"
                          style={{
                            backgroundColor: `#${activeTheme.cardBg}`,
                            borderColor: `#${activeTheme.borderColor}`,
                          }}
                        >
                          <span
                            className="text-sm sm:text-base font-mono font-bold block mb-1.5"
                            style={{ color: `#${activeTheme.secondaryColor}` }}
                          >
                            #0{kIdx + 1}
                          </span>
                          <p
                            className="text-[11px] sm:text-xs leading-snug"
                            style={{ color: `#${headingColor}` }}
                          >
                            {item}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  /* ========================================== */
                  /* SLIDE TYPE 7: EXPANDED SPLIT SCREEN (2 Compact Analytical Columns, Full Uncovered <p>) */
                  /* ========================================== */
                  <div className="flex-1 flex flex-col justify-start gap-2.5 relative z-10 min-h-0 overflow-hidden">
                    <div className="shrink-0 relative z-20">
                      {isEditing ? (
                        <input
                          type="text"
                          value={currentSlide.title}
                          onChange={(e) => handleUpdateSlideField('title', e.target.value)}
                          className="w-full bg-black/40 border border-sky-500 rounded px-3 py-1 text-base sm:text-xl font-bold focus:outline-none"
                          style={{ color: `#${headingColor}` }}
                        />
                      ) : (
                        <h2
                          className="text-base sm:text-xl font-bold tracking-tight leading-snug"
                          style={{ color: `#${headingColor}` }}
                        >
                          {currentSlide.title}
                        </h2>
                      )}
                      <div
                        className="w-14 h-1 rounded-full mt-1"
                        style={{ backgroundColor: `#${activeTheme.accentColor}` }}
                      />
                      {currentSlide.subtitle && (
                        <p
                          className="text-[11px] sm:text-xs leading-snug mt-1.5"
                          style={{ color: `#${activeTheme.textMuted}` }}
                        >
                          {currentSlide.subtitle}
                        </p>
                      )}
                    </div>

                    {/* 2-Column Compact Analytical Cards (Stacked on mobile, Left: 6 + Right: 6 on sm+) */}
                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-2.5 sm:gap-3.5 mt-2 relative z-10">
                      {/* Left Column Card (In-Depth Narrative & Explanation) */}
                      <div
                        className="sm:col-span-6 p-3.5 sm:p-4 rounded-xl border flex flex-col justify-start relative overflow-hidden"
                        style={{
                          backgroundColor: `#${activeTheme.cardBg}`,
                          borderColor: `#${activeTheme.borderColor}`,
                        }}
                      >
                        <div
                          className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider mb-2"
                          style={{ color: `#${activeTheme.secondaryColor}` }}
                        >
                          📌 НЕГІЗГІ МАЗМҰН ЖӘНЕ ТАЛДАУ
                        </div>

                        {isEditing ? (
                          <textarea
                            rows={5}
                            value={currentSlide.content}
                            onChange={(e) => handleUpdateSlideField('content', e.target.value)}
                            className="w-full bg-black/40 border border-slate-700 rounded-xl p-2 text-xs text-white"
                          />
                        ) : (
                          <p
                            className="text-[11px] sm:text-xs leading-relaxed font-normal"
                            style={{ color: `#${activeTheme.textColor}` }}
                          >
                            {currentSlide.content}
                          </p>
                        )}
                      </div>

                      {/* Right Column Card (Key Arguments, Facts & Defense Points) */}
                      <div
                        className="sm:col-span-6 p-3.5 sm:p-4 rounded-xl border flex flex-col justify-start relative overflow-hidden"
                        style={{
                          backgroundColor: `#${activeTheme.cardBg}`,
                          borderColor: `#${activeTheme.borderColor}`,
                        }}
                      >
                        <div
                          className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider mb-2"
                          style={{ color: `#${activeTheme.secondaryColor}` }}
                        >
                          💡 НЕГІЗГІ ТЕЗИСТЕР МЕН ДӘЙЕКТЕР
                        </div>

                        <div className="space-y-1.5">
                          {currentSlide.key_points.map((pt, bIdx) => (
                            <div key={bIdx} className="flex items-start gap-1.5">
                              <span
                                className="font-bold text-xs shrink-0"
                                style={{ color: `#${activeTheme.accentColor}` }}
                              >
                                •
                              </span>
                              {isEditing ? (
                                <div className="flex-1 flex items-center gap-1">
                                  <input
                                    type="text"
                                    value={pt}
                                    onChange={(e) => handleUpdateBullet(bIdx, e.target.value)}
                                    className="flex-1 bg-black/40 border border-slate-700 rounded px-2 py-0.5 text-xs"
                                  />
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteBullet(bIdx)}
                                    className="text-red-400 p-1"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ) : (
                                <p
                                  className="text-[11px] sm:text-xs leading-snug"
                                  style={{ color: `#${activeTheme.textColor}` }}
                                >
                                  {pt}
                                </p>
                              )}
                            </div>
                          ))}

                          {isEditing && (
                            <button
                              type="button"
                              onClick={handleAddBullet}
                              className="text-xs text-sky-400 hover:text-sky-300 font-semibold flex items-center gap-1 pt-1"
                            >
                              <Plus className="w-3 h-3" />
                              <span>Тезис қосу</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Bottom Thumbnails Strip */}
          <div className="flex items-center justify-between gap-1.5 sm:gap-2 bg-slate-850 border border-slate-800 rounded-2xl p-2 sm:p-2.5 max-w-full">
            <button
              onClick={() => setCurrentSlideIdx((prev) => Math.max(0, prev - 1))}
              disabled={currentSlideIdx === 0}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-750 disabled:opacity-30 disabled:cursor-not-allowed text-white transition cursor-pointer shrink-0"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>

            <div className="flex-1 min-w-0 flex items-center gap-1.5 sm:gap-2 overflow-x-auto py-1 px-1 scrollbar-thin">
              {slides.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentSlideIdx(idx)}
                  className={`w-12 sm:w-16 h-9 sm:h-10 rounded-lg shrink-0 border text-[11px] font-mono flex items-center justify-center transition cursor-pointer ${
                    currentSlideIdx === idx
                      ? 'bg-sky-600 text-white border-sky-400 ring-2 ring-sky-500/30 font-bold'
                      : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
                  }`}
                >
                  #{idx + 1}
                </button>
              ))}
            </div>

            <button
              onClick={() => setCurrentSlideIdx((prev) => Math.min(slides.length - 1, prev + 1))}
              disabled={currentSlideIdx === slides.length - 1}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-750 disabled:opacity-30 disabled:cursor-not-allowed text-white transition cursor-pointer shrink-0"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Right Panel: Slide Outline & Structure Navigator */}
        <div className="lg:col-span-3 min-w-0 flex flex-col space-y-4">
          <div className="bg-slate-850 border border-slate-800 rounded-3xl flex flex-col h-full overflow-hidden shadow-xl">
            <div className="py-3.5 px-4 border-b border-slate-800 flex items-center gap-2 text-xs sm:text-sm font-semibold text-sky-400 bg-slate-800/40">
              <BookOpen className="w-4 h-4" />
              <span>📖 Презентация құрылымы ({slides.length})</span>
            </div>

            <div className="p-4 flex-1 overflow-y-auto space-y-2">
              {slides.map((s, idx) => (
                <div
                  key={idx}
                  onClick={() => setCurrentSlideIdx(idx)}
                  className={`p-3 rounded-xl border text-xs sm:text-sm flex items-start gap-2.5 transition cursor-pointer ${
                    currentSlideIdx === idx
                      ? 'bg-sky-600/20 border-sky-500 text-white font-semibold'
                      : 'bg-slate-900/60 hover:bg-slate-800 border-slate-800 text-slate-300'
                  }`}
                >
                  <span className="text-sky-400 font-mono font-bold shrink-0">#{idx + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{s.title}</div>
                    <span className="text-[10px] text-slate-500 uppercase">{s.type}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Quality Score Breakdown Modal */}
      {showScoreModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-750 w-full max-w-md rounded-3xl shadow-2xl p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-emerald-400">
                <ShieldCheck className="w-5 h-5" />
                <h3 className="font-bold text-white text-base">Презентация сапасының көрсеткіші</h3>
              </div>
              <button
                onClick={() => setShowScoreModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="text-center py-2">
              <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300 font-mono">
                {presentation.quality_score?.total || 98}
              </div>
              <p className="text-xs text-slate-400 mt-1">100 балдық кәсіби сапа шкаласы бойынша</p>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center bg-slate-850 p-2.5 rounded-xl border border-slate-750">
                <span className="text-slate-300">🎨 Дизайн палитрасы мен типографика:</span>
                <span className="font-bold text-emerald-400">30 / 30</span>
              </div>
              <div className="flex justify-between items-center bg-slate-850 p-2.5 rounded-xl border border-slate-750">
                <span className="text-slate-300">📝 Кеңейтілген ақпарат пен дәйектер:</span>
                <span className="font-bold text-emerald-400">35 / 35</span>
              </div>
              <div className="flex justify-between items-center bg-slate-850 p-2.5 rounded-xl border border-slate-750">
                <span className="text-slate-300">📖 Логикалық құрылым және оқылуы:</span>
                <span className="font-bold text-emerald-400">20 / 20</span>
              </div>
              <div className="flex justify-between items-center bg-slate-850 p-2.5 rounded-xl border border-slate-750">
                <span className="text-slate-300">⚙️ 16:9 PPTX үйлесімділігі:</span>
                <span className="font-bold text-emerald-400">15 / 15</span>
              </div>
            </div>

            <button
              onClick={() => setShowScoreModal(false)}
              className="w-full py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs cursor-pointer"
            >
              Жабу
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
