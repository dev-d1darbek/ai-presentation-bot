"""
Presentation generation service and workflow logic.
Supports:
- Smart Cross-User Cache (instant delivery when topic + slide_count match any previous project)
- Document-to-Slide generation (.PDF / .DOCX / .PPTX / .TXT)
- Speaker Defense Script generation ("🎤 Қорғау сөзі / Шпаргалка" as .DOCX + chat preview)
- Saved User Projects ("📂 Менің жобаларым")
- PPTX and PDF export
- Advanced Admin Control Center (Revenue, Sold Packages, Partner Withdrawals, User Lookup)
"""
import re
import logging
from typing import Optional, Tuple, Dict, Any, List
from app.core.types import TelegramSession, PresentationData
from app.core.themes import detect_best_theme_for_topic, THEMES_REGISTRY
from app.core.db import (
    init_db,
    log_user,
    log_generation,
    get_admin_stats,
    get_cached_presentation,
    save_cached_presentation,
    save_user_project,
    get_user_projects,
    get_user_project_by_id,
)
from app.core.doc_parser import (
    extract_text_from_uploaded_file,
    generate_speaker_defense_text,
    build_defense_speech_docx,
)
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
    clean_text = text.strip()
    extracted_count = None
    extracted_theme_id = None

    inline_match = re.search(r"[, -]*(\d{1,2})\s*(беттік|бет|слайдтан|слайд)\b", clean_text, re.IGNORECASE)
    if inline_match:
        try:
            num = int(inline_match.group(1))
            if config.MIN_SLIDE_COUNT <= num <= config.MAX_SLIDE_COUNT:
                extracted_count = num
                stripped = re.sub(
                    r"[, -]*\d{1,2}\s*(беттік|бет|слайдтан|слайд)\b", "", clean_text, flags=re.IGNORECASE
                ).strip()
                if len(stripped) >= 2:
                    clean_text = stripped
        except Exception:
            pass

    lower_text = clean_text.lower()
    for theme_id, theme in THEMES_REGISTRY.items():
        if theme.name.lower() in lower_text or theme.nameKz.lower() in lower_text:
            extracted_theme_id = theme_id
            break

    return clean_text, extracted_count, extracted_theme_id


async def generate_deck_for_session(
    session: TelegramSession,
    user_id: Optional[int] = None,
    slide_count: Optional[int] = None,
) -> Tuple[bytes, str, PresentationData, bool]:
    topic = session.pendingTopic or (
        session.lastPresentation.topic if session.lastPresentation else "Жасанды интеллект"
    )
    count = slide_count or session.slideCount or config.DEFAULT_SLIDE_COUNT
    count = max(config.MIN_SLIDE_COUNT, min(count, config.MAX_SLIDE_COUNT))

    selected_theme = (
        THEMES_REGISTRY[session.designId]
        if session.designId != "auto" and session.designId in THEMES_REGISTRY
        else detect_best_theme_for_topic(topic)
    )

    doc_text = session.pendingDocumentText
    from_cache = False

    cached_pres = get_cached_presentation(topic, count, doc_text=doc_text)
    if cached_pres and len(cached_pres.slides) == count:
        logger.info(
            f"⚡ Smart Cache HIT for topic='{topic}' ({count} slides)! Applying design='{selected_theme.id}'."
        )
        presentation = cached_pres
        presentation.design_id = selected_theme.id
        from_cache = True
    else:
        presentation = await ai_client.generate_presentation(
            topic=topic,
            slide_count=count,
            design_id=selected_theme.id,
            language="қазақша",
            document_text=doc_text,
        )
        presentation.design_id = selected_theme.id
        try:
            save_cached_presentation(topic, count, presentation, doc_text=doc_text)
        except Exception as e:
            logger.warning(f"Failed to save to presentation cache: {e}")

    pptx_bytes = build_pptx_deck(presentation)
    base_name = re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", topic)[:40].strip("_") or "presentation"
    clean_filename = f"{base_name}.pptx"

    session.lastPresentation = presentation
    session.pendingTopic = topic
    session.pendingDocumentText = None

    if user_id:
        try:
            save_user_project(user_id, presentation)
            log_generation(user_id, topic, count, selected_theme.id, "pptx", from_cache=from_cache)
        except Exception as e:
            logger.warning(f"Failed to log/save user project: {e}")

    return pptx_bytes, clean_filename, presentation, from_cache


def build_pdf_for_session(
    session: TelegramSession,
    pptx_bytes: Optional[bytes] = None,
) -> Optional[Tuple[bytes, str]]:
    if not session.lastPresentation:
        return None

    pdf_bytes = build_pdf_deck(session.lastPresentation, pptx_bytes=pptx_bytes)
    base_name = (
        re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", session.lastPresentation.topic)[:40].strip("_")
        or "presentation"
    )
    filename = f"{base_name}.pdf"
    return pdf_bytes, filename


def build_speech_for_session(
    session: TelegramSession,
) -> Optional[Tuple[str, bytes, str]]:
    if not session.lastPresentation:
        return None

    full_text = generate_speaker_defense_text(session.lastPresentation)
    docx_bytes = build_defense_speech_docx(session.lastPresentation)
    base_name = (
        re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", session.lastPresentation.topic)[:35].strip("_")
        or "presentation"
    )
    filename = f"Қорғау_сөзі_{base_name}.docx"
    return full_text, docx_bytes, filename


def reexport_deck_with_theme(
    session: TelegramSession,
    theme_id: str,
    user_id: Optional[int] = None,
) -> Optional[Tuple[bytes, str, str]]:
    if not session.lastPresentation:
        return None

    new_theme = (
        THEMES_REGISTRY[theme_id]
        if theme_id != "auto" and theme_id in THEMES_REGISTRY
        else detect_best_theme_for_topic(session.lastPresentation.topic)
    )

    session.lastPresentation.design_id = new_theme.id
    pptx_bytes = build_pptx_deck(session.lastPresentation)
    base_name = (
        re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", session.lastPresentation.topic)[:40].strip("_")
        or "presentation"
    )
    clean_filename = f"{base_name}.pptx"

    if user_id:
        try:
            save_user_project(user_id, session.lastPresentation)
        except Exception:
            pass

    return pptx_bytes, clean_filename, new_theme.nameKz


def load_saved_project_for_session(
    session: TelegramSession,
    project_id: int,
    user_id: Optional[int] = None,
) -> Optional[Tuple[bytes, str, PresentationData, str]]:
    pres = get_user_project_by_id(project_id, user_id=user_id)
    if not pres:
        return None

    theme_obj = THEMES_REGISTRY.get(pres.design_id, THEMES_REGISTRY["swiss_minimalism"])
    session.lastPresentation = pres
    session.pendingTopic = pres.topic
    session.slideCount = pres.slide_count
    session.designId = pres.design_id

    pptx_bytes = build_pptx_deck(pres)
    base_name = re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", pres.topic)[:40].strip("_") or "presentation"
    filename = f"{base_name}.pptx"
    return pptx_bytes, filename, pres, theme_obj.nameKz


def format_user_admin_card(profile: Dict[str, Any]) -> str:
    """Formats a detailed user profile card for the Admin Panel."""
    uid = profile.get("user_id")
    uname = f"@{profile['username']}" if profile.get("username") else "Жоқ"
    fname = profile.get("first_name") or "Белгісіз"
    credits = profile.get("credits", 0)
    invited = profile.get("invited_count", 0)
    sales = profile.get("referral_sales_kzt", 0)
    p_bal = profile.get("partner_balance_kzt", 0)
    p_tot = profile.get("partner_total_earned_kzt", 0)

    return (
        f"👤 <b>ҚОЛДАНУШЫ ПРОФИЛІ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"📛 Есімі: <b>{fname}</b> ({uname})\n"
        f"🎫 Презентация балансы: <b>{credits} дана</b>\n\n"
        f"👥 <b>Реферал және Серіктестік:</b>\n"
        f"• Шақырған достары: <b>{invited} адам</b>\n"
        f"• Достарының саудасы: <b>{sales} ₸</b>\n"
        f"• Шығаруға қолжетімді табыс: <b>{p_bal} ₸</b> (Жалпы тапқаны: {p_tot} ₸)\n\n"
        f"👇 Төмендегі батырмалар арқылы балансын өзгертуге немесе тікелей хат жазуға болады:"
    )


def format_admin_dashboard_text() -> Tuple[str, int]:
    """
    Formats comprehensive admin statistics and returns (text, pending_withdrawals_count).
    """
    stats = get_admin_stats()

    pkg_lines = ""
    for p in stats.get("packages_breakdown", []):
        t_obj = config.TARIFF_PLANS.get(p["tariff_id"], {})
        t_title = t_obj.get("title", p["tariff_id"])
        pkg_lines += f"  • {t_title}: <b>{p['cnt']} дана</b> ({p['sum_kzt']} ₸)\n"
    if not pkg_lines:
        pkg_lines = "  (Әзірге сатылым жоқ)\n"

    themes_str = ""
    for idx, t in enumerate(stats["top_themes"]):
        theme_obj = THEMES_REGISTRY.get(t["design_id"])
        t_name = theme_obj.nameKz if theme_obj else t["design_id"]
        themes_str += f"  {idx + 1}. {t_name}: {t['count']} рет\n"
    if not themes_str:
        themes_str = "  (Әзірге деректер жоқ)\n"

    recent_str = ""
    for idx, r in enumerate(stats["recent_generations"][:5]):
        u_name = f"@{r['username']}" if r.get("username") else (r.get("first_name") or "Қолданушы")
        cache_icon = "⚡" if r.get("from_cache") else "🤖"
        recent_str += f"  {cache_icon} {u_name}: «{r['topic']}» ({r['slide_count']} бет)\n"
    if not recent_str:
        recent_str = "  (Әзірге презентация жасалмаған)\n"

    pend_w_cnt = stats.get("pending_withdrawals_count", 0)
    pend_w_kzt = stats.get("pending_withdrawals_kzt", 0)
    paid_w_cnt = stats.get("paid_withdrawals_count", 0)
    paid_w_kzt = stats.get("paid_withdrawals_kzt", 0)

    text = (
        "📊 <b>AI PRESENTATION BOT — АДМИН ПАНЕЛЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💰 <b>Қаржы және Сатылым:</b>\n"
        f"• Бүгінгі табыс: <b>{stats['revenue_today_kzt']} ₸</b> ({stats['payments_today_count']} төлем)\n"
        f"• Жалпы табыс: <b>{stats['revenue_total_kzt']} ₸</b> ({stats['payments_total_count']} төлем)\n\n"
        "💸 <b>Серіктестік төлемдер (Выплаты):</b>\n"
        f"• Күтілудегі сұраныстар: <b>{pend_w_cnt} дана ({pend_w_kzt} ₸)</b>\n"
        f"• Төленген шығарулар: <b>{paid_w_cnt} дана ({paid_w_kzt} ₸)</b>\n"
        f"• Жалпы есептелген бонус: <b>{stats['partner_paid_kzt']} ₸</b>\n\n"
        "📦 <b>Сатылған пакеттер:</b>\n"
        f"{pkg_lines}\n"
        "👥 <b>Пайдаланушылар:</b>\n"
        f"• Жалпы тіркелген: <b>{stats['total_users']}</b> адам (Бүгін: {stats['users_today']})\n\n"
        "📑 <b>Жасалған презентациялар:</b>\n"
        f"• Жалпы саны: <b>{stats['total_generations']}</b> файл (Бүгін: {stats['generations_today']})\n"
        f"• ⚡ Кэштен лезде берілгені: <b>{stats['cached_generations']}</b> рет (Базада: {stats['total_cached_items']} жоба)\n\n"
        "⏱ <b>Соңғы сұраныстар:</b>\n"
        f"{recent_str}\n"
        "🎁 <b>Командамен баланс беру:</b> <code>/give ID САНЫ</code>"
    )
    return text, pend_w_cnt
