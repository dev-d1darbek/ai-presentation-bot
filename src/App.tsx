import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { PromptBar } from './components/PromptBar';
import { SlideDeckViewer } from './components/SlideDeckViewer';
import { ThemesGalleryModal } from './components/ThemesGalleryModal';
import { ChatRefineDrawer } from './components/ChatRefineDrawer';
import { MyPresentationsModal } from './components/MyPresentationsModal';
import { HelpModal } from './components/HelpModal';
import { PresentationData, AppLanguage } from './designs/types';
import {
  generatePresentationAPI,
  getSavedPresentations,
  savePresentationToLocal,
  deletePresentationFromLocal,
} from './services/api';

export const App: React.FC = () => {
  const [currentLang, setCurrentLang] = useState<AppLanguage>('kk');
  const [activePresentation, setActivePresentation] = useState<PresentationData | null>(null);
  const [savedPresentations, setSavedPresentations] = useState<PresentationData[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isThemesGalleryOpen, setIsThemesGalleryOpen] = useState(false);
  const [isChatDrawerOpen, setIsChatDrawerOpen] = useState(false);
  const [isMyPresentationsOpen, setIsMyPresentationsOpen] = useState(false);
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  useEffect(() => {
    const loaded = getSavedPresentations();
    setSavedPresentations(loaded);
  }, []);

  const handleGenerate = async (params: {
    topic: string;
    slide_count: number;
    design_id?: string;
  }) => {
    setIsGenerating(true);
    try {
      const pres = await generatePresentationAPI({
        topic: params.topic,
        slide_count: params.slide_count,
        design_id: params.design_id,
        language: currentLang === 'ru' ? 'орысша' : currentLang === 'en' ? 'ағылшынша' : 'қазақша',
      });
      setActivePresentation(pres);
      savePresentationToLocal(pres);
      setSavedPresentations(getSavedPresentations());
    } catch (err: any) {
      console.error('Generation error:', err);
      alert('Қате орын алды: ' + (err.message || 'Презентация жасау мүмкін болмады'));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleUpdatePresentation = (updated: PresentationData) => {
    setActivePresentation(updated);
    savePresentationToLocal(updated);
    setSavedPresentations(getSavedPresentations());
  };

  const handleDeletePresentation = (id: string) => {
    const updated = deletePresentationFromLocal(id);
    setSavedPresentations(updated);
    if (activePresentation?.id === id) {
      setActivePresentation(null);
    }
  };

  const handleSelectTheme = (themeId: string) => {
    if (activePresentation) {
      const updated = {
        ...activePresentation,
        design_id: themeId,
      };
      handleUpdatePresentation(updated);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      <Header
        currentLang={currentLang}
        onSelectLang={setCurrentLang}
        onNewPresentation={() => setActivePresentation(null)}
        onOpenMyPresentations={() => setIsMyPresentationsOpen(true)}
        onOpenThemesGallery={() => setIsThemesGalleryOpen(true)}
        onOpenHelp={() => setIsHelpOpen(true)}
        presentationCount={savedPresentations.length}
      />

      <main className="flex-1 flex flex-col justify-center">
        {activePresentation ? (
          <SlideDeckViewer
            presentation={activePresentation}
            onUpdatePresentation={handleUpdatePresentation}
            onNewPresentation={() => setActivePresentation(null)}
            onOpenThemesGallery={() => setIsThemesGalleryOpen(true)}
            onOpenChatDrawer={() => setIsChatDrawerOpen(true)}
          />
        ) : (
          <PromptBar
            onGenerate={handleGenerate}
            isGenerating={isGenerating}
            onOpenThemesGallery={() => setIsThemesGalleryOpen(true)}
          />
        )}
      </main>

      {/* 30 Themes Showcase / Switcher Modal */}
      <ThemesGalleryModal
        isOpen={isThemesGalleryOpen}
        onClose={() => setIsThemesGalleryOpen(false)}
        activeThemeId={activePresentation?.design_id || 'swiss_minimalism'}
        onSelectTheme={handleSelectTheme}
      />

      {/* AI Conversational Assistant Refine Drawer */}
      {activePresentation && (
        <ChatRefineDrawer
          presentation={activePresentation}
          onUpdatePresentation={handleUpdatePresentation}
          isOpen={isChatDrawerOpen}
          onClose={() => setIsChatDrawerOpen(false)}
        />
      )}

      {/* My Presentations Modal */}
      <MyPresentationsModal
        isOpen={isMyPresentationsOpen}
        onClose={() => setIsMyPresentationsOpen(false)}
        presentations={savedPresentations}
        onSelectPresentation={(pres) => setActivePresentation(pres)}
        onDeletePresentation={handleDeletePresentation}
        currentLang={currentLang}
      />

      {/* Help Modal */}
      <HelpModal
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        currentLang={currentLang}
      />
    </div>
  );
};

export default App;
