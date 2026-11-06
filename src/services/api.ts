import pptxgen from 'pptxgenjs';
import { PresentationData, SlideContent } from '../designs/types';
import { THEMES_REGISTRY } from '../designs/registry';

export async function generatePresentationAPI(params: {
  topic: string;
  slide_count?: number;
  language?: string;
  design_id?: string;
  prompt_context?: string[];
}): Promise<PresentationData> {
  const response = await fetch('/api/generate-presentation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      slide_count: 15,
      language: 'қазақша',
      ...params,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || 'Failed to generate presentation');
  }

  return response.json();
}

export async function refinePresentationAPI(params: {
  presentation: PresentationData;
  user_message: string;
}): Promise<{ presentation: PresentationData; reply: string }> {
  const response = await fetch('/api/refine-presentation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || 'Failed to refine presentation');
  }

  return response.json();
}

import { buildPptxDeck } from '../designs/pptxEngine';

export async function exportPresentationToPPTX(presentation: PresentationData): Promise<void> {
  const safeFilename = (presentation.topic || presentation.title_presentation || 'Presentation')
    .replace(/[^a-zA-Z0-9\u0400-\u04FF_-]/g, '_')
    .substring(0, 40);

  try {
    const res = await fetch('/api/export-pptx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: presentation.topic,
        title_presentation: presentation.title_presentation,
        slides: presentation.slides,
        design_id: presentation.design_id,
      }),
    });
    if (!res.ok) throw new Error('Server PPTX export failed');
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safeFilename}.pptx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.warn('Server PPTX export failed, using client-side PPTX engine fallback:', error);
    const pres = buildPptxDeck(presentation);
    await pres.writeFile({ fileName: `${safeFilename}.pptx` });
  }
}

const STORAGE_KEY = 'ai_presentation_studio_history_v2';

export function getSavedPresentations(): PresentationData[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function savePresentationToLocal(presentation: PresentationData): void {
  try {
    const existing = getSavedPresentations();
    const updated = [presentation, ...existing.filter((p) => p.id !== presentation.id)].slice(0, 30);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (e) {
    console.warn('Failed to save to localStorage:', e);
  }
}

export function deletePresentationFromLocal(id: string): PresentationData[] {
  try {
    const existing = getSavedPresentations();
    const updated = existing.filter((p) => p.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    return updated;
  } catch {
    return [];
  }
}
