"""
Data models and types for AI Presentation Studio.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

LayoutType = Literal[
    'cover',
    'split_screen',
    'big_typography',
    'timeline',
    'comparison',
    'two_person_comparison',
    'statistics',
    'quote',
    'profile_cards',
    'process_diagram',
    'key_takeaway',
    'conclusion',
    'bullets'
]

class ThemeConfig(BaseModel):
    id: str
    name: str
    nameKz: str
    nameRu: str
    category: str
    description: str
    primaryColor: str
    headingColor: Optional[str] = None
    secondaryColor: str
    accentColor: str
    bgColor: str
    cardBg: str
    textColor: str
    textMuted: str
    borderColor: str
    isDark: bool
    fontHeading: str
    fontBody: str
    recommendedTopics: List[str] = Field(default_factory=list)

class SlideStat(BaseModel):
    value: str
    label: str

class TimelineItem(BaseModel):
    step: str
    title: str
    desc: str

class ComparisonEntity(BaseModel):
    name: str
    points: List[str] = Field(default_factory=list)

class SlideComparison(BaseModel):
    entityA: ComparisonEntity
    entityB: ComparisonEntity

class SlideQuote(BaseModel):
    text: str
    author: Optional[str] = None

class SlideContent(BaseModel):
    slide_number: int
    type: LayoutType
    title: str
    subtitle: Optional[str] = None
    content: str
    key_points: List[str] = Field(default_factory=list)
    stats: Optional[List[SlideStat]] = None
    timeline: Optional[List[TimelineItem]] = None
    comparison: Optional[SlideComparison] = None
    quote: Optional[SlideQuote] = None

class QualityScore(BaseModel):
    total: int = 98
    design: int = 25
    content: int = 20
    imagery: int = 15
    readability: int = 14
    structure: int = 10

class PresentationData(BaseModel):
    id: str
    topic: str
    title_presentation: str
    design_id: str
    language: str = "қазақша"
    slide_count: int
    slides: List[SlideContent]
    plan_summary: List[str] = Field(default_factory=list)
    quality_score: Optional[QualityScore] = None
    createdAt: Optional[str] = None

class TelegramSession(BaseModel):
    slideCount: int = 15
    designId: str = "auto"
    pendingTopic: Optional[str] = None
    themePage: int = 0
    lastPresentation: Optional[PresentationData] = None
