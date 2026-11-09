"""
System prompts and LLM prompt builder for presentation generation.
- For NO-PHOTO presentations (with_photos=False): generates deep, comprehensive, information-rich academic/analytical slides
  (60-85 words in 'content' + 4 detailed bullet points of 18-28 words each) so slides are packed with valuable facts, figures, and arguments.
- For PHOTO presentations (with_photos=True): generates balanced analytical text + 3-4 detailed points alongside visual queries.
- Forbids repetitive standard codes like 'ГОСТ 7.32-2017' in slide text.
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
    persona_style: str = "academic_universal",
    is_storybook: bool = False,
    child_name: Optional[str] = None,
    child_avatar_desc: Optional[str] = None,
) -> str:
    if is_storybook or template_id == "storybook":
        hero = (child_name or "Жас батыр").strip()
        avatar_prefix = (
            child_avatar_desc.strip()
            if child_avatar_desc and child_avatar_desc.strip()
            else f"cute Kazakh child named {hero}, round face, expressive brown eyes, warm smile"
        )
        return f"""
You are a Master Children's Fairy-Tale Author and Pixar Storybook Illustrator.
Write a 100% pure, cohesive, magical children's fairy-tale story (Ертегі) across exactly {count} illustrated pages.

Input Parameters:
- Main Hero (Child's Name): {hero}
- Fairy-Tale Theme / Adventure: {topic}
- Page Count: Exactly {count} pages (slides)
- Output Language: {language} (Write ALL 'title' and 'content' strictly in {language}!)
- Persistent Character Digital Avatar (MUST be included at the start of EVERY 'image_query'): "{avatar_prefix}"

CRITICAL FAIRY-TALE STORYBOOK RULES (NO EXTRA THOUGHTS OR ACADEMIC TEXT!):
1. PURE FAIRY-TALE NARRATIVE ONLY: Every single slide is a sequential page of one continuous fairy tale about {hero}. Do NOT include any academic explanations, facts, statistics, bullet points, morals-analysis, or meta-commentary! Write ONLY pure fairy-tale storytelling ("Ерте-ерте ертеде...", magical dialogues, adventure scenes, and a warm fairy-tale ending).
2. EVERY SLIDE MUST HAVE `"type": "storybook_full_photo"` and `"key_points": []`.
3. CONSISTENT DIGITAL AVATAR IN EVERY `image_query`:
   - On EVERY slide, `"image_query"` MUST be in English and MUST start with the child's digital avatar description `"{avatar_prefix}"` followed by the specific scene action and setting (e.g., `"{avatar_prefix}, standing in a glowing magical forest talking to a golden bird, Pixar 3D storybook art"`).
4. PAGE CONTENT LENGTH:
   - `'title'`: Short, magical chapter title (3–6 words in {language}).
   - `'content'`: Warm, vivid fairy-tale narrative paragraph of 35–55 words (3–4 sentences in {language}) telling what {hero} does, sees, and feels on this page of the story.

Return strictly valid, compact JSON matching this structure:
{{
  "title_presentation": "Сиқырлы ертегі: {hero} және {topic}",
  "design_id": "{selected_theme.id}",
  "slides": [
    {{
      "slide_number": 1,
      "type": "storybook_full_photo",
      "title": "Chapter 1 Title in {language}",
      "subtitle": "",
      "content": "Pure fairy-tale story text (35-55 words in {language}) featuring {hero}...",
      "key_points": [],
      "image_query": "{avatar_prefix}, magical opening scene description in English"
    }}
  ]
}}
"""

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

    p_info = config.PERSONA_STYLES.get(persona_style, config.PERSONA_STYLES["academic_universal"])
    persona_rule = f"\nUSER SPECIALTY / PERSONA STYLE ({p_info['title']}):\n- {p_info['prompt_rule']}\n"
    if is_storybook or template_id == "storybook":
        hero = child_name or "Жас батыр"
        persona_rule += (
            f"- CHILDREN'S ILLUSTRATED FAIRY-TALE STORYBOOK MODE: The main hero of this fairy tale is a child named «{hero}». "
            f"Every single slide MUST have \"type\": \"storybook_full_photo\" and a vivid English \"image_query\" (e.g. \"pixar style children book illustration cute kid {hero} magical forest\") "
            f"and warm fairy-tale narrative in 'content' featuring {hero}!"
        )
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
        "5. ACADEMIC & ANALYTICAL DEPTH: Use rigorous academic terminology, concrete statistics, historical dates, mechanisms, cause-and-effect analysis, and practical insights suitable for university and professional presentations. CRITICAL: NEVER write standard codes like 'ГОСТ', 'ГОСТ 7.32-2017', or 'GOST' inside any slide title, subtitle, content, or key_points!"
        if tmpl.get("gost_compliant", True)
        else "5. PROFESSIONAL BUSINESS & INDUSTRY DEPTH: Use concrete KPIs, ROI metrics, SWOT/market sizing, and actionable frameworks. NEVER write standard codes like 'ГОСТ' inside slide text."
    )

    if with_photos:
        photo_instruction = (
            "1. PHOTO-ENABLED MODE: Include a concise 3-5 word English search/generation prompt in `\"image_query\"` on every slide (e.g. `\"modern artificial intelligence laboratory\"`) and use layout types `\"photo_hero\"`, `\"photo_split\"`, `\"photo_magazine\"`, `\"statistics\"`, `\"timeline\"`, `\"two_person_comparison\"`, `\"conclusion\"`."
        )
        density_instruction = f"""4. RICH & BALANCED ANALYTICAL CONTENT ON EVERY SLIDE (in {language}):
   - 'title': Clear, informative headline of 4–8 words.
   - 'subtitle': Substantive subtitle of 6–12 words explaining the slide's focus.
   - 'content': Write a substantive, detailed analytical paragraph of 42–60 words in {language} explaining core concepts, mechanisms, historical facts, and quantitative data.
   - 'key_points': Provide 3 to 4 detailed, informative bullet statements of 14–22 words each in {language} with concrete facts, figures, examples, and conclusions."""
        type_fields_instruction = """8. ONLY INCLUDE TYPE-SPECIFIC FIELDS WHEN NEEDED:
   - Include "stats" (array of 3 items: {"value": "Metric (e.g. $1.8 трлн, 35%)", "label": "Detailed explanation of the metric (10-16 words)"}) ONLY when "type" is "statistics".
   - Include "timeline" (array of 3 items: {"step": "01", "title": "Stage title", "desc": "Detailed stage explanation (20-30 words) with dates and facts"}) ONLY when "type" is "timeline".
   - Include "comparison" ({"entityA": {"name": "Entity A name", "points": [4 detailed items of 14-20 words each]}, "entityB": {"name": "Entity B name", "points": [4 detailed items of 14-20 words each]}}) ONLY when "type" is "two_person_comparison"."""
    else:
        photo_instruction = (
            "1. NO-PHOTO INFORMATION-RICH MODE: Do NOT generate 'image_query' or 'image_url'. Since there are NO photos on the slides, every slide MUST contain deep, comprehensive, detailed text and analytical information so the slides feel full, substantive, and ready for academic/professional defense!"
        )
        density_instruction = f"""4. COMPREHENSIVE, DEEP & DETAILED TEXT ON EVERY SLIDE (in {language} — DO NOT WRITE SHORT OR SUPERFICIAL TEXTS!):
   - 'title': Informative academic/professional headline of 5–9 words in {language}.
   - 'subtitle': Detailed 1-2 line analytical subtitle of 8–15 words in {language} summarizing the section thesis.
   - 'content': Write a deep, comprehensive analytical paragraph of 60–85 words (4–5 full sentences) in {language} thoroughly explaining the theoretical definitions, historical context, causal mechanisms, statistical evidence, and practical significance.
   - 'key_points': Provide 4 detailed, fact-packed bullet statements of 18–28 words each (1-2 full sentences per bullet) in {language} containing specific dates, percentages, scholarly concepts, real-world examples, and conclusions."""
        type_fields_instruction = """8. ONLY INCLUDE TYPE-SPECIFIC FIELDS WHEN NEEDED (MAKE THEM DETAILED AND INFORMATIVE):
   - Include "stats" (array of 3 items: {"value": "Metric (e.g. $1.8 трлн, 35%, 1000+)", "label": "Detailed context and source of the metric (12-20 words)"}) ONLY when "type" is "statistics".
   - Include "timeline" (array of 3 items: {"step": "01", "title": "Stage period & title", "desc": "Comprehensive 28-42 word explanation of key events, theories, and outcomes in this stage"}) ONLY when "type" is "timeline".
   - Include "comparison" ({"entityA": {"name": "Entity A name", "points": [4 detailed analytical points of 18-26 words each]}, "entityB": {"name": "Entity B name", "points": [4 detailed analytical points of 18-26 words each]}}) ONLY when "type" is "two_person_comparison"."""

    image_field_example = ',\n      "image_query": "concise 4-word English visual query"' if with_photos else ""

    return f"""
You are a World-Class Presentation Architect, Academic Researcher, and Visual Designer.
Create a deeply informative, comprehensive, self-contained presentation in compact JSON format.

Input Parameters:
- Topic / Title: {topic}
- Target Slide Count: Exactly {count} slides
- Target Output Language: {language} (Write ALL titles, subtitles, content, and key_points strictly in {language}!)
- Target Design Theme: {selected_theme.id}
- Template Mode: {tmpl['title']}
- Conversation context / modifications: {context_str}
{template_section}{persona_rule}{doc_section}
CRITICAL CONTENT DEPTH & QUALITY RULES:
{photo_instruction}
2. STRICT NO-BOILERPLATE RULE: NEVER mention "ГОСТ", "ГОСТ 7.32-2017", "GOST", or generic filler like "Бұл презентация..." in any slide title, subtitle, content, or key_points. Start directly with substantive domain facts, definitions, and analysis.
3. NO DESIGN NAME ON COVER: On Slide 1 ("cover"), do NOT mention the design theme name or platform name in 'title' or 'subtitle'.
{density_instruction}
{academic_note}
6. Slide 1 must have "type": "cover". Final slide must have "type": "conclusion".
7. Use varied layout types across slides: "cover", "split_screen", "two_person_comparison" (when comparing 2 approaches/entities), "timeline", "statistics", "big_typography", "key_takeaway", "conclusion".
{type_fields_instruction}

Return strictly valid, compact JSON matching this structure:
{{
  "title_presentation": "Compelling Academic/Professional Title in {language}",
  "design_id": "{selected_theme.id}",
  "slides": [
    {{
      "slide_number": 1,
      "type": "cover",
      "title": "Informative Title in {language}",
      "subtitle": "Detailed analytical subtitle in {language}",
      "content": "Comprehensive, multi-sentence analytical paragraph in {language}...",
      "key_points": [
        "Detailed factual statement 1 with concrete data, dates, and context...",
        "Detailed analytical statement 2 explaining mechanisms and causes...",
        "Detailed comparative or empirical statement 3 with real-world examples...",
        "Detailed practical conclusion 4 highlighting strategic significance..."
      ]{image_field_example}
    }}
  ]
}}
"""
