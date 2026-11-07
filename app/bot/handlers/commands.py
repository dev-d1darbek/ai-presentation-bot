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


def get_start_message(chat_id: int) -> tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    text = (
        f"👋 Сәлем! Мен кәсіби <b>AI Presentation Bot</b>-пын.\n\n"
        f"📌 <b>Қалай қолдануға болады?</b>\n"
        f"• Кез келген тақырыпты жазыңыз (мысалы: <i>«Жасанды интеллект»</i> немесе <i>«Қазақстан тарихы 10 бет»</i>).\n"
        f"• Немесе дайын <b>.PDF / .DOCX / .TXT</b> құжатын (реферат, курстық, мақала) жіберіңіз — бот одан автоматты түрде слайд жасап береді!\n\n"
        f"⚙️ <b>Қазіргі баптаулар:</b>\n"
        f"• Бет саны: {session.slideCount} слайд\n"
        f"• Дизайн: {get_selected_theme_label(session.designId)}"
    )
    return text, get_persistent_reply_keyboard()


def get_help_message() -> tuple[str, Dict[str, Any]]:
    help_text = (
        "ℹ️ <b>Бот мүмкіндіктері мен нұсқаулық:</b>\n\n"
        "1. <b>Тақырып бойынша жасау:</b> Чатқа презентация тақырыбын жазып, бет санын таңдаңыз.\n"
        "2. <b>Құжаттан слайд жасау (PDF / DOCX / TXT):</b> Чатқа реферат, мақала немесе есеп файлын жіберсеңіз, бот оның мазмұнынан дайын презентация құрастырады.\n"
        "3. <b>🎤 Қорғау сөзі (Шпаргалка):</b> Дайын презентацияның астындағы батырма арқылы әр слайдты қорғағанда айтатын дайын сөйлеу мәтінін (.DOCX және мәтін) ала аласыз.\n"
        "4. <b>📂 Менің жобаларым:</b> Бұрын жасаған барлық презентацияларыңыз сақталады — кез келген уақытта қайта жүктеп немесе басқа дизайнға ауыстыра аласыз."
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
