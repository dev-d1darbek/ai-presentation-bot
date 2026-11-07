"""
Aiogram 3 Command Handlers.
"""
from typing import Dict, Any
from app.core.themes import get_selected_theme_label
from app.bot.session import get_telegram_session
from app.bot.keyboards.reply import get_persistent_reply_keyboard
from app.bot.keyboards.inline import (
    build_clean_themes_keyboard,
    build_default_slides_keyboard,
)

# Helpers that convert dict keyboards to aiogram types dynamically or format text
def get_start_message(chat_id: int) -> tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    text = (
        f"👋 Сәлем! Мен кәсіби AI Presentation Bot-пын.\n\n"
        f"Кез келген презентация тақырыбын жаза салыңыз (мысалы: «Жасанды интеллект» немесе «Қазақстан тарихы 10 бет»).\n\n"
        f"⚙️ Қазіргі баптаулар:\n"
        f"• Бет саны: {session.slideCount} слайд\n"
        f"• Дизайн: {get_selected_theme_label(session.designId)}"
    )
    return text, get_persistent_reply_keyboard()

def get_help_message() -> tuple[str, Dict[str, Any]]:
    help_text = (
        "ℹ️ Қолдану өте оңай:\n\n"
        "1. Чатқа презентация тақырыбын жазыңыз (мысалы: «Жасанды интеллект»).\n"
        "2. Шыққан терезеден бет санын бассаңыз (8, 10, 12, 15, 20), бот дайын .PPTX файлын бірден жібереді!\n"
        "3. Дайын файлдың астындағы «🎨 Дизайнын ауыстыру» батырмасы арқылы кез келген 30 стильге 1 секундта ауыстыра аласыз."
    )
    return help_text, get_persistent_reply_keyboard()

def get_slides_message(chat_id: int) -> tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    text = f"📄 Неше беттік презентация жасағыңыз келеді? (Қазір: {session.slideCount} бет):"
    return text, build_default_slides_keyboard(session, is_regenerate=False)

def get_design_message(chat_id: int) -> tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    mode = "topic" if session.pendingTopic else "default"
    text = f"🎨 30 кәсіби дизайн шаблонынан таңдаңыз (Қазір: {get_selected_theme_label(session.designId, session.pendingTopic)}):"
    return text, build_clean_themes_keyboard(session, session.themePage, mode)
