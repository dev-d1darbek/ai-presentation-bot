export type AppLanguage = 'kk' | 'ru' | 'en';

export type LayoutType =
  | 'cover'
  | 'split_screen'
  | 'big_typography'
  | 'timeline'
  | 'comparison'
  | 'two_person_comparison'
  | 'statistics'
  | 'quote'
  | 'profile_cards'
  | 'process_diagram'
  | 'key_takeaway'
  | 'conclusion'
  | 'bullets';

export interface ThemeConfig {
  id: string;
  name: string;
  nameKz: string;
  nameRu: string;
  category: 'Modern' | 'Editorial' | 'Tech' | 'Minimal' | 'Corporate' | 'Creative' | 'Academic';
  description: string;
  primaryColor: string; // hex without #
  headingColor?: string; // High-contrast headline title color
  secondaryColor: string;
  accentColor: string;
  bgColor: string;
  cardBg: string;
  textColor: string;
  textMuted: string;
  borderColor: string;
  isDark: boolean;
  fontHeading: string;
  fontBody: string;
  recommendedTopics: string[];
}

export interface SlideContent {
  slide_number: number;
  type: LayoutType;
  title: string;
  subtitle?: string;
  content: string; // Detailed paragraph (40-80 words)
  key_points: string[]; // 3-4 bullet theses
  stats?: { value: string; label: string }[];
  comparison?: {
    entityA: { name: string; points: string[]; image_query?: string; image_url?: string; image_data?: string };
    entityB: { name: string; points: string[]; image_query?: string; image_url?: string; image_data?: string };
  };
  timeline?: { step: string; title: string; desc: string }[];
  quote?: { text: string; author: string };
  image_query?: string;
  image_url?: string;
  image_data?: string;
  speaker_notes?: string;
}

export interface PresentationData {
  id: string;
  topic: string;
  title_presentation: string;
  design_id: string;
  language: 'қазақша' | 'орысша' | 'ағылшынша';
  slide_count: number;
  slides: SlideContent[];
  plan_summary: string[];
  quality_score: {
    total: number;
    design: number;
    content: number;
    imagery: number;
    readability: number;
    structure: number;
  };
  createdAt: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  suggestedAction?: string;
}
