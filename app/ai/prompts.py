"""
System prompts and LLM prompt builder for presentation generation.
Enforces clean, concise slide text budgets (no overflow) and forbids repetitive standard codes like 'ГОСТ 7.32-2017' in slide text.
"""
import json
from typing import List, Dict, Any, Optional
import config
from app.core.types import ThemeConfig


def build_system_prompt(
    topic: str,
    count: int,
    language: str,
    selected_theme: ThemeConfig,
    prompt_context: Optional[List[Dict[str, Any]]] = None,
    document_text: Optional[str] = None,
    template_id: str = "standard",
    with_photos: bool = False,
) -> str:
    context_str = json.dumps(prompt_context or [], ensure_ascii=False)

    doc_section = ""
    if document_text and document_text.strip():
        trimmed_doc = document_text.strip()[:16000]
        doc_section = f"""
SOURCE DOCUMENT CONTENT (Synthesize and structure the {count} slides strictly and accurately based on this uploaded document):
\"\"\"
{trimmed_doc}
\"\"\"
"""

    tmpl = config.TEMPLATE_LIBRARY.get(template_id, config.TEMPLATE_LIBRARY["standard"])
    template_section = ""
    if tmpl and tmpl.get("structure"):
        steps_str = "\n".join(f"  - {s}" for s in tmpl["structure"])
        template_section = f"""
MANDATORY TEMPLATE STRUCTURE ({tmpl['title']}):
Follow this logical section progression across your {count} slides:
{steps_str}
"""

    academic_note = (
        "5. ACADEMIC & ANALYTICAL DEPTH: Use clear, natural academic terminology, concrete statistics, historical dates, and practical insights suitable for university and professional presentations. CRITICAL: NEVER write standard codes like 'ГОСТ', 'ГОСТ 7.32-2017', or 'GOST' inside any slide title, subtitle, content, or key_points!"
        if tmpl.get("gost_compliant", True)
        else "5. PROFESSIONAL BUSINESS & INDUSTRY DEPTH: Use concrete KPIs, ROI metrics, SWOT/market sizing, and actionable frameworks. NEVER write standard codes like 'ГОСТ' inside slide text."
    )

    photo_instruction = (
        "1. PHOTO-ENABLED MODE: Include a concise 3-5 word English search/generation prompt in `\"image_query\"` on every slide (e.g. `\"modern artificial intelligence laboratory\"`) and use layout types `\"photo_hero\"`, `\"photo_split\"`, `\"photo_magazine\"`, `\"statistics\"`, `\"timeline\"`, `\"two_person_comparison\"`, `\"conclusion\"`."
        if with_photos
        else "1. NO IMAGES OR PHOTOS: Do NOT generate 'image_query' or 'image_url'."
    )

    image_field_example = ',\n      "image_query": "concise 4-word English visual query"' if with_photos else ""

    return f"""
You are a World-Class Presentation Architect, Academic Researcher, and Visual Designer.
Create a deeply informative, visually balanced, self-contained presentation in compact JSON format.

Input Parameters:
- Topic / Title: {topic}
- Target Slide Count: Exactly {count} slides
- Target Output Language: {language} (Write ALL titles, subtitles, content, and key_points strictly in {language}!)
- Target Design Theme: {selected_theme.id}
- Template Mode: {tmpl['title']}
- Conversation context / modifications: {context_str}
{template_section}{doc_section}
CRITICAL LAYOUT & TEXT LENGTH RULES (PREVENT TEXT OVERFLOW):
{photo_instruction}
2. STRICT NO-BOILERPLATE RULE: NEVER mention "ГОСТ", "ГОСТ 7.32-2017", "GOST", or meta-phrases like "Бұл презентация..." in any slide title, subtitle, content, or key_points. Start directly with the subject facts.
3. NO DESIGN NAME ON COVER: On Slide 1 ("cover"), do NOT mention the design theme name or platform name in 'title' or 'subtitle'.
4. STRICT CHARACTER & WORD BUDGETS FOR PERFECT SLIDE FIT (in {language}):
   - 'title': Short, impactful headline of 4–7 words (MAX 55 characters) so it fits on 1–2 clean lines.
   - 'subtitle': Concise 1-line subtitle of 5–9 words (MAX 75 characters).
   - 'content': Clear, substantive analytical paragraph of 25–38 words (MAX 240 characters) explaining the core concept, cause, or mechanism concisely.
   - 'key_points': Exactly 3 concise bullet statements of 8–13 words each (MAX 105 characters per bullet) with concrete facts, figures, or examples.
{academic_note}
6. Slide 1 must have "type": "cover". Final slide must have "type": "conclusion".
7. Use varied layout types across slides: "cover", "split_screen", "photo_split", "photo_magazine", "two_person_comparison" (if topic compares 2 people/entities), "timeline", "statistics", "big_typography", "key_takeaway", "conclusion".
8. ONLY INCLUDE TYPE-SPECIFIC FIELDS WHEN NEEDED:
   - Include "stats" (array of 3 items: {{"value": "Short metric (e.g. $1.8 трлн, 35%)", "label": "Concise label (max 55 chars)"}}) ONLY when "type" is "statistics".
   - Include "timeline" (array of 3 items: {{"step": "01", "title": "Short stage title (max 34 chars)", "desc": "Concise stage description (12-17 words, max 120 chars)"}}) ONLY when "type" is "timeline".
   - Include "comparison" ({{"entityA": {{"name": "Short name (max 35 chars)", "points": [3 or 4 concise items, max 95 chars each]}}, "entityB": {{"name": "Short name (max 35 chars)", "points": [3 or 4 concise items, max 95 chars each]}}}}) ONLY when "type" is "two_person_comparison".

Return strictly valid, compact JSON matching this structure:
{{
  "title_presentation": "Compelling Academic/Professional Title in {language}",
  "design_id": "{selected_theme.id}",
  "slides": [
    {{
      "slide_number": 1,
      "type": "cover",
      "title": "Concise Title in {language} (max 55 chars)",
      "subtitle": "Concise subtitle in {language} (max 75 chars)",
      "content": "Focused analytical paragraph (25-38 words, max 240 chars in {language})...",
      "key_points": [
        "Concise factual point 1 (max 105 chars)...",
        "Concise analytical point 2 (max 105 chars)...",
        "Concise practical conclusion 3 (max 105 chars)..."
      ]{image_field_example}
    }}
  ]
}}
"""
