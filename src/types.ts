export * from './designs/types';

export type AppLanguage = 'kk' | 'ru' | 'en';

export interface WizardState {
  topic: string;
  slide_count: number;
  design_id?: string;
  step: 'prompt' | 'generating';
}
