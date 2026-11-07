"""
System prompts and LLM prompt builder for presentation generation.
"""
import json
from typing import List, Dict, Any, Optional
from app.core.types import ThemeConfig

def build_system_prompt(
    topic: str,
    count: int,
    language: str,
    selected_theme: ThemeConfig,
    prompt_context: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Builds token-efficient, photo-free, presentation architecture prompt.
    """
    context_str = json.dumps(prompt_context or [], ensure_ascii=False)

    return f"""
You are a World-Class Presentation Architect, Academic Researcher, and Visual Designer.
Create a deeply informative, comprehensive, self-contained presentation in compact JSON format.

Input Parameters:
- Topic: {topic}
- Target Slide Count: Exactly {count} slides
- Language: {language}
- Target Design Theme: {selected_theme.id}
- Conversation context / modifications: {context_str}

CRITICAL CONTENT & TOKEN EFFICIENCY REQUIREMENTS:
1. NO IMAGES OR PHOTOS: Do NOT generate 'image_query' or 'image_url'.
2. NO SPEAKER NOTES: Do NOT generate 'speaker_notes'. Put all key explanations, facts, dates, and arguments directly into 'content' and 'key_points' so the presenter can defend directly from the slides.
3. NO DESIGN NAME ON COVER: On Slide 1 ("cover"), do NOT mention the design theme name or platform name in 'title' or 'subtitle'.
4. SELF-CONTAINED ANALYTICAL CONTENT ON EVERY SLIDE:
   - 'content': Write a clear, substantive analytical paragraph of 35-55 words in {language} explaining the core concepts, causes, mechanisms, or historical facts.
   - 'key_points': Provide 3 to 4 substantive sentences (10-16 words each) in {language} with concrete facts, figures, examples, and conclusions.
5. Slide 1 must have "type": "cover". Final slide must have "type": "conclusion".
6. Use varied layout types across slides: "cover", "split_screen", "two_person_comparison" (if topic compares 2 people/entities), "timeline", "statistics", "big_typography", "key_takeaway", "conclusion".
7. ONLY INCLUDE TYPE-SPECIFIC FIELDS WHEN NEEDED (to keep JSON compact and prevent token truncation):
   - Include "stats" (array of 3 items: {{"value": "...", "label": "..."}}) ONLY when "type" is "statistics".
   - Include "timeline" (array of 3 items: {{"step": "01", "title": "...", "desc": "15-22 words"}}) ONLY when "type" is "timeline".
   - Include "comparison" ({{"entityA": {{"name": "...", "points": [4 items]}}, "entityB": {{"name": "...", "points": [4 items]}}}}) ONLY when "type" is "two_person_comparison".
   - Omit "stats", "timeline", and "comparison" on all other slide types!

Return strictly valid, compact JSON matching this structure:
{{
  "title_presentation": "Compelling Academic/Professional Title",
  "design_id": "{selected_theme.id}",
  "slides": [
    {{
      "slide_number": 1,
      "type": "cover",
      "title": "Slide Title",
      "subtitle": "Substantive topic subtitle",
      "content": "Substantive analytical paragraph (35-55 words in {language})...",
      "key_points": [
        "Detailed thesis statement 1 with concrete facts...",
        "Detailed thesis statement 2 with analytical insight...",
        "Detailed thesis statement 3 with practical significance..."
      ]
    }}
  ]
}}
"""
