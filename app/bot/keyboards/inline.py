"""
Inline keyboards for 1-tap UX, slide counts, 30 design themes,
PPTX/PDF export, Speaker Defense Speech (Қорғау сөзі), and Saved User Projects.
"""
import math
from typing import Dict, Any, List
from app.core.types import TelegramSession
from app.core.themes import THEMES_REGISTRY, THEMES_LIST, get_selected_theme_label


def build_topic_ready_text(session: TelegramSession) -> str:
    topic = session.pendingTopic or "Жасанды интеллект"
    theme_label = get_selected_theme_label(session.designId, topic)
    doc_badge = "\n📎 <i>Құжат мәтіні негізінде дайындалады</i>" if session.pendingDocumentText else ""
    return (
        f"📌 Тақырып: «{topic}»\n"
        f"🎨 Дизайн: {theme_label}{doc_badge}\n\n"
        f"👇 Бет санын бассаңыз, презентация бірден дайындалады:"
    )


def build_topic_ready_keyboard(session: TelegramSession) -> Dict[str, Any]:
    counts_row1 = [8, 10, 12]
    counts_row2 = [15, 20, 25]

    row_counts_1 = [
        {
            "text": f"✅ {n} бет" if session.slideCount == n else f"📄 {n} бет",
            "callback_data": f"gen_now:{n}",
        }
        for n in counts_row1
    ]

    row_counts_2 = [
        {
            "text": f"✅ {n} бет" if session.slideCount == n else f"📄 {n} бет",
            "callback_data": f"gen_now:{n}",
        }
        for n in counts_row2
    ]

    theme_label = get_selected_theme_label(session.designId, session.pendingTopic)

    return {
        "inline_keyboard": [
            [
                {
                    "text": f"🚀 Бірден жасау ({session.slideCount} бет • .PPTX / .PDF)",
                    "callback_data": f"gen_now:{session.slideCount}",
                }
            ],
            row_counts_1,
            row_counts_2,
            [
                {
                    "text": f"🎨 Дизайнды өзгерту ({theme_label})",
                    "callback_data": "open_themes:0:topic",
                }
            ],
        ]
    }


def build_clean_themes_keyboard(session: TelegramSession, page: int, mode: str = "default") -> Dict[str, Any]:
    all_themes = THEMES_LIST
    page_size = 6
    total_pages = math.ceil(len(all_themes) / page_size)
    safe_page = ((page % total_pages) + total_pages) % total_pages
    slice_themes = all_themes[safe_page * page_size : (safe_page + 1) * page_size]

    prefix = "reexport_theme" if mode == "reexport" else "pick_theme"

    rows: List[List[Dict[str, str]]] = [
        [
            {
                "text": "✅ 🤖 Автоматты (AI таңдайды)" if session.designId == "auto" else "🤖 Автоматты (AI таңдайды)",
                "callback_data": f"{prefix}:auto",
            }
        ]
    ]

    for i in range(0, len(slice_themes), 2):
        pair = slice_themes[i : i + 2]
        rows.append(
            [
                {
                    "text": f"✅ {t.nameKz}" if session.designId == t.id else t.nameKz,
                    "callback_data": f"{prefix}:{t.id}",
                }
                for t in pair
            ]
        )

    rows.append(
        [
            {"text": "⬅️ Алдыңғы", "callback_data": f"open_themes:{safe_page - 1}:{mode}"},
            {"text": f"{safe_page + 1} / {total_pages}", "callback_data": "noop"},
            {"text": "Келесі ➡️", "callback_data": f"open_themes:{safe_page + 1}:{mode}"},
        ]
    )

    if mode == "topic" and session.pendingTopic:
        rows.append([{"text": "⬅️ Тақырыпқа оралу", "callback_data": "back_to_topic"}])

    return {"inline_keyboard": rows}


def build_default_slides_keyboard(session: TelegramSession, is_regenerate: bool = False) -> Dict[str, Any]:
    prefix = "gen_now" if is_regenerate else "save_default_slides"
    row1 = [
        {
            "text": f"✅ {n} бет" if session.slideCount == n else f"{n} бет",
            "callback_data": f"{prefix}:{n}",
        }
        for n in [5, 8, 10, 12]
    ]
    row2 = [
        {
            "text": f"✅ {n} бет" if session.slideCount == n else f"{n} бет",
            "callback_data": f"{prefix}:{n}",
        }
        for n in [15, 18, 20, 25]
    ]
    return {"inline_keyboard": [row1, row2]}


def build_post_generation_keyboard(has_pdf: bool = False) -> Dict[str, Any]:
    """
    Buttons below sent file:
    Row 1: PDF / PPTX download + Speaker Defense Script (🎤 Қорғау сөзі)
    Row 2: Change Design (30 themes) + Change Slide Count
    """
    first_btn = (
        {"text": "📥 PPTX жүктеу (.PPTX)", "callback_data": "export_pptx"}
        if has_pdf
        else {"text": "📥 PDF нұсқасы (.PDF)", "callback_data": "export_pdf"}
    )
    return {
        "inline_keyboard": [
            [
                first_btn,
                {"text": "🎤 Қорғау сөзі (Шпаргалка)", "callback_data": "export_speech"},
            ],
            [
                {"text": "🎨 Дизайнын ауыстыру", "callback_data": "open_themes:0:reexport"},
                {"text": "📄 Бет санын өзгерту", "callback_data": "open_slides_regen"},
            ],
        ]
    }


def build_user_projects_keyboard(projects: List[Dict[str, Any]], page: int, total_count: int, page_size: int = 6) -> Dict[str, Any]:
    """
    Inline keyboard displaying user's saved presentations ("📂 Менің жобаларым").
    """
    rows: List[List[Dict[str, str]]] = []
    for proj in projects:
        proj_id = proj["id"]
        topic = proj["topic"][:32]
        slides = proj["slide_count"]
        theme_obj = THEMES_REGISTRY.get(proj["design_id"])
        theme_short = theme_obj.nameKz[:14] if theme_obj else ""
        label = f"📄 {topic} ({slides} бет • {theme_short})"
        rows.append([{"text": label, "callback_data": f"load_proj:{proj_id}"}])

    total_pages = max(1, math.ceil(total_count / page_size))
    if total_pages > 1:
        safe_page = ((page % total_pages) + total_pages) % total_pages
        rows.append(
            [
                {"text": "⬅️ Алдыңғы", "callback_data": f"open_projects:{safe_page - 1}"},
                {"text": f"{safe_page + 1} / {total_pages}", "callback_data": "noop"},
                {"text": "Келесі ➡️", "callback_data": f"open_projects:{safe_page + 1}"},
            ]
        )

    return {"inline_keyboard": rows}


def build_admin_keyboard() -> Dict[str, Any]:
    """Buttons for /admin panel."""
    return {
        "inline_keyboard": [
            [
                {"text": "🔄 Жаңарту", "callback_data": "admin_refresh"},
                {"text": "📢 Хабарлама жіберу", "callback_data": "admin_broadcast"},
            ]
        ]
    }
