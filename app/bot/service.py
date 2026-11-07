"""
Presentation generation service and workflow logic.
Supports PPTX and PDF generation, logging, and admin analytics.
"""
import re
import logging
from typing import Optional, Tuple, Dict, Any
from app.core.types import TelegramSession, PresentationData
from app.core.themes import detect_best_theme_for_topic, THEMES_REGISTRY
from app.core.db import init_db, log_user, log_generation, get_admin_stats, get_all_user_ids
from app.ai.client import AIClient
from app.pptx_generator.engine import build_pptx_deck
from app.pptx_generator.pdf_engine import build_pdf_deck
import config

logger = logging.getLogger(__name__)

# Ensure DB tables exist
init_db()

ai_client = AIClient(
    deepseek_api_key=config.DEEPSEEK_API_KEY,
    gemini_api_key=config.GEMINI_API_KEY,
    openai_api_key=config.OPENAI_API_KEY,
)

def parse_user_input(text: str) -> Tuple[str, Optional[int], Optional[str]]:
    """
    Parses text to extract clean topic, optional inline slide count, and optional theme mention.
    """
    clean_text = text.strip()
    extracted_count = None
    extracted_theme_id = None

    # Check inline slide count
    inline_match = re.search(r'[, -]*(\d{1,2})\s*(беттік|бет|слайдтан|слайд)\b', clean_text, re.IGNORECASE)
    if inline_match:
        try:
            num = int(inline_match.group(1))
            if config.MIN_SLIDE_COUNT <= num <= config.MAX_SLIDE_COUNT:
                extracted_count = num
                stripped = re.sub(r'[, -]*\d{1,2}\s*(беттік|бет|слайдтан|слайд)\b', '', clean_text, flags=re.IGNORECASE).strip()
                if len(stripped) >= 2:
                    clean_text = stripped
        except Exception:
            pass

    # Check theme name mention
    lower_text = clean_text.lower()
    for theme_id, theme in THEMES_REGISTRY.items():
        if theme.name.lower() in lower_text or theme.nameKz.lower() in lower_text:
            extracted_theme_id = theme_id
            break

    return clean_text, extracted_count, extracted_theme_id

async def generate_deck_for_session(
    session: TelegramSession,
    user_id: Optional[int] = None,
    slide_count: Optional[int] = None
) -> Tuple[bytes, str, PresentationData]:
    """
    Executes presentation generation for session and returns (pptx_bytes, filename, presentation).
    """
    topic = session.pendingTopic or (session.lastPresentation.topic if session.lastPresentation else "Жасанды интеллект")
    count = slide_count or session.slideCount or config.DEFAULT_SLIDE_COUNT
    count = max(config.MIN_SLIDE_COUNT, min(count, config.MAX_SLIDE_COUNT))

    selected_theme = (
        THEMES_REGISTRY[session.designId]
        if session.designId != "auto" and session.designId in THEMES_REGISTRY
        else detect_best_theme_for_topic(topic)
    )

    presentation = await ai_client.generate_presentation(
        topic=topic,
        slide_count=count,
        design_id=selected_theme.id,
        language="қазақша"
    )

    pptx_bytes = build_pptx_deck(presentation)
    base_name = re.sub(r'[^a-zA-Z0-9\u0400-\u04FF]', '_', topic)[:40].strip('_') or "presentation"
    clean_filename = f"{base_name}.pptx"

    session.lastPresentation = presentation
    session.pendingTopic = topic

    if user_id:
        try:
            log_generation(user_id, topic, count, selected_theme.id, "pptx")
        except Exception as e:
            logger.warning(f"Failed to log generation: {e}")

    return pptx_bytes, clean_filename, presentation

def build_pdf_for_session(
    session: TelegramSession,
    pptx_bytes: Optional[bytes] = None
) -> Optional[Tuple[bytes, str]]:
    """
    Generates PDF bytes for the last presentation in session.
    """
    if not session.lastPresentation:
        return None

    pdf_bytes = build_pdf_deck(session.lastPresentation, pptx_bytes=pptx_bytes)
    base_name = re.sub(r'[^a-zA-Z0-9\u0400-\u04FF]', '_', session.lastPresentation.topic)[:40].strip('_') or "presentation"
    filename = f"{base_name}.pdf"
    return pdf_bytes, filename

def reexport_deck_with_theme(
    session: TelegramSession,
    theme_id: str
) -> Optional[Tuple[bytes, str, str]]:
    """
    Instantly re-renders last presentation with new design (0 AI tokens, ~1 second).
    Returns (pptx_bytes, filename, theme_name_kz) or None if no last presentation.
    """
    if not session.lastPresentation:
        return None

    new_theme = (
        THEMES_REGISTRY[theme_id]
        if theme_id != "auto" and theme_id in THEMES_REGISTRY
        else detect_best_theme_for_topic(session.lastPresentation.topic)
    )

    session.lastPresentation.design_id = new_theme.id
    pptx_bytes = build_pptx_deck(session.lastPresentation)
    base_name = re.sub(r'[^a-zA-Z0-9\u0400-\u04FF]', '_', session.lastPresentation.topic)[:40].strip('_') or "presentation"
    clean_filename = f"{base_name}.pptx"

    return pptx_bytes, clean_filename, new_theme.nameKz

def format_admin_dashboard_text() -> str:
    """
    Formats clean text representation of statistics for /admin dashboard.
    """
    stats = get_admin_stats()

    themes_str = ""
    for idx, t in enumerate(stats["top_themes"]):
        theme_obj = THEMES_REGISTRY.get(t["design_id"])
        t_name = theme_obj.nameKz if theme_obj else t["design_id"]
        themes_str += f"  {idx + 1}. {t_name}: {t['count']} рет\n"
    if not themes_str:
        themes_str = "  (Әзірге деректер жоқ)\n"

    counts_str = ""
    for idx, sc in enumerate(stats["top_slide_counts"]):
        counts_str += f"  {idx + 1}. {sc['slide_count']} бет: {sc['count']} рет\n"
    if not counts_str:
        counts_str = "  (Әзірге деректер жоқ)\n"

    recent_str = ""
    for idx, r in enumerate(stats["recent_generations"][:5]):
        u_name = f"@{r['username']}" if r.get("username") else (r.get("first_name") or "Қолданушы")
        recent_str += f"  • {u_name}: «{r['topic']}» ({r['slide_count']} бет)\n"
    if not recent_str:
        recent_str = "  (Әзірге презентация жасалмаған)\n"

    text = (
        "📊 <b>AI PRESENTATION BOT — БАСҚАРУ ПАНЕЛІ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👥 <b>Пайдаланушылар:</b>\n"
        f"• Жалпы тіркелген: <b>{stats['total_users']}</b> адам\n"
        f"• Бүгін белсенді: <b>{stats['users_today']}</b> адам\n\n"
        "📑 <b>Жасалған презентациялар:</b>\n"
        f"• Жалпы саны: <b>{stats['total_generations']}</b> файл\n"
        f"• Бүгін жасалған: <b>{stats['generations_today']}</b> файл\n\n"
        "🎨 <b>Үздік дизайн стильдері:</b>\n"
        f"{themes_str}\n"
        "📄 <b>Сұранысқа ие бет сандары:</b>\n"
        f"{counts_str}\n"
        "⏱ <b>Соңғы сұраныстар:</b>\n"
        f"{recent_str}"
    )
    return text
