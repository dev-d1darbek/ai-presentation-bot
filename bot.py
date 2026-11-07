"""
Production AI Presentation Bot using Aiogram 3.
Includes:
1. Document-to-Slide (.PDF / .DOCX / .PPTX / .TXT upload -> Presentation)
2. Speaker Defense Script ("🎤 Қорғау сөзі / Шпаргалка" as .DOCX + preview)
3. Saved User Projects ("📂 Менің жобаларым" — retrieve anytime)
4. Smart Cross-User Cache (instant 1-sec delivery when topic + slide_count match any previous project, even with different design)
5. Pure Minimalist UI/UX + PPTX/PDF Dual Export + /admin Dashboard
"""
import asyncio
import io
import logging
import re
from typing import Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    BotCommand,
)
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
from app.core.themes import detect_best_theme_for_topic, THEMES_REGISTRY, get_selected_theme_label
from app.core.db import log_user, get_all_user_ids, get_user_projects
from app.core.doc_parser import extract_text_from_uploaded_file
from app.pptx_generator.engine import build_pptx_deck
from app.bot.session import get_telegram_session
from app.bot.keyboards.reply import get_persistent_reply_keyboard
from app.bot.keyboards.inline import (
    build_topic_ready_text,
    build_topic_ready_keyboard,
    build_clean_themes_keyboard,
    build_default_slides_keyboard,
    build_post_generation_keyboard,
    build_user_projects_keyboard,
    build_admin_keyboard,
)
from app.bot.service import (
    parse_user_input,
    generate_deck_for_session,
    build_pdf_for_session,
    build_speech_for_session,
    reexport_deck_with_theme,
    load_saved_project_for_session,
    format_admin_dashboard_text,
)
from app.bot.handlers.commands import (
    get_start_message,
    get_help_message,
    get_slides_message,
    get_design_message,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = Router()


class AdminStates(StatesGroup):
    waiting_for_broadcast = State()


def dict_to_inline_markup(d: dict) -> InlineKeyboardMarkup:
    rows = []
    for row in d.get("inline_keyboard", []):
        btn_row = []
        for btn in row:
            btn_row.append(InlineKeyboardButton(text=btn["text"], callback_data=btn.get("callback_data", "noop")))
        rows.append(btn_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dict_to_reply_markup(d: dict) -> ReplyKeyboardMarkup:
    rows = []
    for row in d.get("keyboard", []):
        btn_row = [KeyboardButton(text=btn["text"]) for btn in row]
        rows.append(btn_row)
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=d.get("resize_keyboard", True),
        is_persistent=d.get("is_persistent", True),
    )


async def execute_generation(
    bot: Bot,
    chat_id: int,
    session,
    user_id: Optional[int] = None,
    slide_count: Optional[int] = None,
    existing_msg_id: Optional[int] = None,
):
    topic = session.pendingTopic or (
        session.lastPresentation.topic if session.lastPresentation else "Жасанды интеллект"
    )
    count = slide_count or session.slideCount
    selected_theme = (
        THEMES_REGISTRY[session.designId]
        if session.designId != "auto" and session.designId in THEMES_REGISTRY
        else detect_best_theme_for_topic(topic)
    )

    status_text = (
        f"⏳ «{topic}» презентациясы дайындалуда...\n\n"
        f"📄 Бет саны: {count} слайд\n"
        f"🎨 Дизайн: {selected_theme.nameKz}\n\n"
        f"Күте тұрыңыз, дайын файл бірнеше секундта жіберіледі..."
    )

    status_msg_id = None
    if existing_msg_id:
        try:
            await bot.edit_message_text(text=status_text, chat_id=chat_id, message_id=existing_msg_id)
            status_msg_id = existing_msg_id
        except Exception:
            msg = await bot.send_message(chat_id=chat_id, text=status_text)
            status_msg_id = msg.message_id
    else:
        msg = await bot.send_message(chat_id=chat_id, text=status_text)
        status_msg_id = msg.message_id

    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

    try:
        pptx_bytes, filename, presentation, from_cache = await generate_deck_for_session(
            session, user_id=user_id or chat_id, slide_count=count
        )
        speed_badge = "⚡ <i>Жылдам кэштен лезде дайындалды</i>\n" if from_cache else ""
        caption = (
            f"✅ <b>Презентация дайын!</b>\n"
            f"{speed_badge}"
            f"📌 Тақырып: {topic}\n"
            f"📄 Бет саны: {presentation.slide_count} слайд\n"
            f"🎨 Дизайн: {selected_theme.nameKz}\n\n"
            f"👇 PDF нұсқасы, Қорғау сөзі (Шпаргалка) немесе Дизайн ауыстыру:"
        )
        doc = BufferedInputFile(pptx_bytes, filename=filename)
        await bot.send_document(
            chat_id=chat_id,
            document=doc,
            caption=caption,
            reply_markup=dict_to_inline_markup(build_post_generation_keyboard(has_pdf=False)),
        )
        if status_msg_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        await bot.send_message(
            chat_id=chat_id,
            text="❌ Кешіріңіз, презентация жасау барысында қате орын алды. Тақырыпты қайта жазып көріңіз.",
        )


# ----------------- Command Handlers -----------------

@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user:
        log_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    text, kb = get_start_message(message.chat.id)
    await message.answer(text, reply_markup=dict_to_reply_markup(kb))


@router.message(Command("help"))
@router.message(F.text == "❓ Көмек")
async def cmd_help(message: Message):
    text, kb = get_help_message()
    await message.answer(text, reply_markup=dict_to_reply_markup(kb))


@router.message(Command("slides"))
@router.message(F.text.in_({"📄 Бет саны", "📄 Бет санын таңдау"}))
async def cmd_slides(message: Message):
    text, kb = get_slides_message(message.chat.id)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


@router.message(Command("design"))
@router.message(F.text.in_({"🎨 Дизайн таңдау", "🎨 Дизайн таңдау (30 стиль)"}))
async def cmd_design(message: Message):
    text, kb = get_design_message(message.chat.id)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


@router.message(Command("projects"))
@router.message(F.text == "📂 Менің жобаларым")
async def cmd_projects(message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    projects, total = get_user_projects(user_id, limit=6, offset=0)
    if not projects:
        await message.answer(
            "📂 <b>Сізде әзірге сақталған жобалар жоқ.</b>\n\n"
            "Чатқа кез келген презентация тақырыбын жазыңыз немесе .PDF / .DOCX құжатын жіберіңіз — "
            "жасалған барлық презентацияларыңыз осы жерде автоматты түрде сақталады!",
            reply_markup=dict_to_reply_markup(get_persistent_reply_keyboard()),
        )
        return

    text = (
        f"📂 <b>Менің сақталған жобаларым ({total}):</b>\n\n"
        f"Кез келген жобаны басып, оны <b>.PPTX</b>, <b>.PDF</b>, <b>🎤 Қорғау сөзі</b> ретінде жүктеп алуға "
        f"немесе дизайнын 1 секундта ауыстыруға болады:"
    )
    kb = build_user_projects_keyboard(projects, page=0, total_count=total)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
        await message.answer("⛔️ Бұл команда тек бот әкімшісіне арналған.")
        return

    text = format_admin_dashboard_text()
    if not config.ADMIN_IDS:
        text += f"\n\n💡 <i>Кеңес: Қауіпсіздік үшін өз Telegram ID-іңізді (<code>{user_id}</code>) .env файлына ADMIN_IDS={user_id} деп жазып қойыңыз.</i>"

    await message.answer(text, reply_markup=dict_to_inline_markup(build_admin_keyboard()))


# ----------------- Broadcast Handler -----------------

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer(
        "📢 Барлық пайдаланушыларға тарататын хабарлама мәтінін жазыңыз (немесе бас тарту үшін /cancel):"
    )
    await callback.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Әрекет тоқтатылды.")


@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    text = message.text
    user_ids = get_all_user_ids()
    sent_count = 0

    await message.answer(f"⏳ {len(user_ids)} пайдаланушыға тарату басталды...")
    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=text)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.answer(f"✅ Хабарлама {sent_count}/{len(user_ids)} адамға сәтті жеткізілді!")


@router.callback_query(F.data == "admin_refresh")
async def cb_admin_refresh(callback: CallbackQuery):
    user_id = callback.from_user.id
    if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return

    text = format_admin_dashboard_text()
    try:
        await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(build_admin_keyboard()))
        await callback.answer("Жаңартылды!")
    except Exception:
        await callback.answer()


# ----------------- Document Upload Handler (PDF / DOCX / TXT -> Slide) -----------------

@router.message(F.document)
async def handle_document_upload(message: Message, bot: Bot):
    if message.from_user:
        log_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    doc = message.document
    filename = doc.file_name or "document.txt"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in (".pdf", ".docx", ".pptx", ".txt", ".md"):
        await message.answer(
            "⚠️ Кешіріңіз, тек <b>.PDF, .DOCX, .PPTX</b> немесе <b>.TXT</b> форматындағы құжаттарды жіберуге болады."
        )
        return

    status_msg = await message.answer(f"📥 <b>«{filename}»</b> құжаты оқылуда, күте тұрыңыз...")

    try:
        file_io = io.BytesIO()
        await bot.download(doc, destination=file_io)
        file_bytes = file_io.getvalue()

        doc_title, extracted_text = extract_text_from_uploaded_file(filename, file_bytes)
        if not extracted_text or len(extracted_text.strip()) < 20:
            await status_msg.edit_text(
                "⚠️ Құжаттың ішінен мәтін табылмады (немесе ол тек сурет/сканнан тұрады). "
                "Мәтіні бар .DOCX, .PDF немесе .TXT файлын жіберіп көріңіз."
            )
            return

        session = get_telegram_session(message.chat.id)
        caption_text = (message.caption or "").strip()

        inline_count = None
        if caption_text:
            clean_cap, inline_count, theme_mention = parse_user_input(caption_text)
            if clean_cap:
                doc_title = clean_cap
            if inline_count:
                session.slideCount = inline_count
            if theme_mention:
                session.designId = theme_mention

        session.pendingTopic = doc_title
        session.pendingDocumentText = extracted_text

        if inline_count:
            await execute_generation(
                bot,
                message.chat.id,
                session,
                user_id=message.from_user.id if message.from_user else message.chat.id,
                slide_count=inline_count,
                existing_msg_id=status_msg.message_id,
            )
            return

        word_count = len(extracted_text.split())
        ready_text = (
            f"✅ <b>Құжат сәтті оқылды!</b> ({word_count} сөз)\n\n"
            + build_topic_ready_text(session)
        )
        await status_msg.edit_text(
            ready_text,
            reply_markup=dict_to_inline_markup(build_topic_ready_keyboard(session)),
        )
    except Exception as e:
        logger.error(f"Document upload error: {e}", exc_info=True)
        await status_msg.edit_text("❌ Құжатты өңдеу кезінде қате орын алды. Қайта тексеріп көріңіз.")


# ----------------- Text Input Handlers -----------------

@router.message(F.text)
async def handle_user_text(message: Message, bot: Bot):
    if message.from_user:
        log_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    text = message.text.strip()
    chat_id = message.chat.id
    session = get_telegram_session(chat_id)

    # 1. Slide count only (e.g. "10 бет", "15 слайд")
    only_slide_match = re.match(
        r"^(\d{1,2})\s*(бет|слайд|беттік|слайдтан)(\s+болсын|\s+жаса|\s+қыл)?$", text, re.IGNORECASE
    )
    if only_slide_match:
        num = max(config.MIN_SLIDE_COUNT, min(int(only_slide_match.group(1)), config.MAX_SLIDE_COUNT))
        session.slideCount = num
        if session.pendingTopic or session.lastPresentation:
            await execute_generation(
                bot, chat_id, session, user_id=message.from_user.id if message.from_user else chat_id
            )
        else:
            await message.answer(
                f"✅ Бет саны {num} слайд болып белгіленді. Енді презентация тақырыбын жазыңыз!",
                reply_markup=dict_to_reply_markup(get_persistent_reply_keyboard()),
            )
        return

    # 2. Extract topic and optional inline parameters
    clean_topic, inline_count, theme_mention = parse_user_input(text)
    if inline_count:
        session.slideCount = inline_count
    if theme_mention:
        session.designId = theme_mention

    session.pendingTopic = clean_topic
    session.pendingDocumentText = None  # New text topic clears any previous uploaded document

    # If user provided explicit count inline, generate immediately!
    if inline_count:
        await execute_generation(
            bot, chat_id, session, user_id=message.from_user.id if message.from_user else chat_id
        )
        return

    # Otherwise show 1-tap UX card
    card_text = build_topic_ready_text(session)
    card_kb = build_topic_ready_keyboard(session)
    await message.answer(card_text, reply_markup=dict_to_inline_markup(card_kb))


# ----------------- Callback Handlers -----------------

@router.callback_query()
async def handle_callback(callback: CallbackQuery, bot: Bot):
    data = callback.data or ""
    chat_id = callback.message.chat.id
    msg_id = callback.message.message_id
    user_id = callback.from_user.id if callback.from_user else chat_id
    is_doc = bool(getattr(callback.message, "document", None))
    session = get_telegram_session(chat_id)

    if data == "noop":
        await callback.answer()
        return

    # Export Speaker Defense Script (🎤 Қорғау сөзі / Шпаргалка)
    if data == "export_speech":
        if not session.lastPresentation:
            await callback.answer("Алдымен презентация жасаңыз.", show_alert=True)
            return

        await callback.answer("🎤 Қорғау сөзі дайындалуда...")
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

        speech_res = build_speech_for_session(session)
        if not speech_res:
            await callback.message.answer("❌ Қорғау сөзін дайындауда қате орын алды.")
            return

        full_text, docx_bytes, filename = speech_res
        # Build short preview for caption (first 800 chars)
        preview_lines = full_text.split("\n")[:14]
        preview_str = "\n".join(preview_lines)
        if len(preview_str) > 850:
            preview_str = preview_str[:850] + "..."

        caption = (
            f"{preview_str}\n\n"
            f"📥 <i>Барлық {session.lastPresentation.slide_count} слайдтың толық қорғау сөзі жоғарыдағы Word (.DOCX) файлында!</i>"
        )
        doc = BufferedInputFile(docx_bytes, filename=filename)
        await bot.send_document(chat_id=chat_id, document=doc, caption=caption, parse_mode=None)
        return

    # Paginate Saved Projects ("📂 Менің жобаларым")
    if data.startswith("open_projects:"):
        page = int(data.split(":")[1])
        page_size = 6
        projects, total = get_user_projects(user_id, limit=page_size, offset=max(0, page) * page_size)
        if not projects and page != 0:
            page = 0
            projects, total = get_user_projects(user_id, limit=page_size, offset=0)

        await callback.answer()
        text = (
            f"📂 <b>Менің сақталған жобаларым ({total}):</b>\n\n"
            f"Жобаны басып, оны қайта жүктеп алуға немесе дизайнын ауыстыруға болады:"
        )
        kb = build_user_projects_keyboard(projects, page=page, total_count=total, page_size=page_size)
        if not is_doc:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
            )
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        return

    # Load a Specific Saved Project
    if data.startswith("load_proj:"):
        proj_id = int(data.split(":")[1])
        await callback.answer("📂 Жоба жүктелуде...")
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

        loaded = load_saved_project_for_session(session, proj_id, user_id=user_id)
        if not loaded:
            await callback.message.answer("❌ Жоба табылмады.")
            return

        pptx_bytes, filename, pres, theme_name_kz = loaded
        caption = (
            f"📂 <b>Сақталған жоба жүктелді!</b>\n"
            f"📌 Тақырып: {pres.topic}\n"
            f"📄 Бет саны: {pres.slide_count} слайд\n"
            f"🎨 Дизайн: {theme_name_kz}\n\n"
            f"👇 PDF нұсқасы, Қорғау сөзі немесе Дизайн ауыстыру:"
        )
        doc = BufferedInputFile(pptx_bytes, filename=filename)
        await bot.send_document(
            chat_id=chat_id,
            document=doc,
            caption=caption,
            reply_markup=dict_to_inline_markup(build_post_generation_keyboard(has_pdf=False)),
        )
        return

    # Export PDF Version
    if data == "export_pdf":
        if not session.lastPresentation:
            await callback.answer("Алдымен презентация жасаңыз.", show_alert=True)
            return

        await callback.answer("📑 PDF форматы дайындалуда...")
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

        pdf_res = build_pdf_for_session(session)
        if not pdf_res:
            await callback.message.answer("❌ PDF жасауда қате орын алды.")
            return

        pdf_bytes, filename = pdf_res
        doc = BufferedInputFile(pdf_bytes, filename=filename)
        caption = (
            f"📑 <b>PDF форматындағы презентация дайын!</b>\n"
            f"📌 Тақырып: {session.lastPresentation.topic}\n"
            f"📄 Бет саны: {session.lastPresentation.slide_count} слайд"
        )
        await bot.send_document(
            chat_id=chat_id,
            document=doc,
            caption=caption,
            reply_markup=dict_to_inline_markup(build_post_generation_keyboard(has_pdf=True)),
        )
        return

    # Export PPTX Version
    if data == "export_pptx":
        if not session.lastPresentation:
            await callback.answer("Алдымен презентация жасаңыз.", show_alert=True)
            return

        await callback.answer("📥 PPTX дайындалуда...")
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
        pptx_bytes = build_pptx_deck(session.lastPresentation)
        base_name = (
            re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", session.lastPresentation.topic)[:40].strip("_")
            or "presentation"
        )
        doc = BufferedInputFile(pptx_bytes, filename=f"{base_name}.pptx")
        caption = (
            f"✅ <b>PPTX презентация дайын!</b>\n"
            f"📌 Тақырып: {session.lastPresentation.topic}\n"
            f"📄 Бет саны: {session.lastPresentation.slide_count} слайд"
        )
        await bot.send_document(
            chat_id=chat_id,
            document=doc,
            caption=caption,
            reply_markup=dict_to_inline_markup(build_post_generation_keyboard(has_pdf=False)),
        )
        return

    # 1-Tap Generate
    if data.startswith("gen_now:"):
        n = int(data.split(":")[1])
        session.slideCount = n
        await callback.answer(f"🚀 {n} беттік презентация жасалуда...")
        await execute_generation(
            bot,
            chat_id,
            session,
            user_id=user_id,
            slide_count=n,
            existing_msg_id=msg_id if not is_doc else None,
        )
        return

    # Save default slides
    if data.startswith("save_default_slides:"):
        n = int(data.split(":")[1])
        session.slideCount = n
        await callback.answer(f"✅ Әдепкі бет саны: {n} бет")
        if session.pendingTopic:
            text = build_topic_ready_text(session)
            kb = build_topic_ready_keyboard(session)
            if not is_doc:
                await bot.edit_message_text(
                    text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
                )
            else:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        elif not is_doc:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"✅ Әдепкі бет саны {n} слайд болып сақталды.\n\nЕнді кез келген презентация тақырыбын жазыңыз!",
            )
        return

    # Slide count re-generate selector
    if data == "open_slides_regen":
        await callback.answer()
        topic = session.pendingTopic or (
            session.lastPresentation.topic if session.lastPresentation else "Презентация"
        )
        kb = build_default_slides_keyboard(session, is_regenerate=True)
        await bot.send_message(
            chat_id=chat_id,
            text=f"📄 «{topic}» презентациясын неше бетпен қайта жасаймыз?\nБатырманы бассаңыз, бірден дайындалады:",
            reply_markup=dict_to_inline_markup(kb),
        )
        return

    # 30-Themes Menu
    if data.startswith("open_themes:"):
        parts = data.split(":")
        page = int(parts[1]) if len(parts) > 1 else 0
        mode = parts[2] if len(parts) > 2 else "default"
        session.themePage = page
        await callback.answer()

        text = (
            "🎨 Жаңа дизайнды бассаңыз, дайын файл бірден сол дизайнмен қайта жіберіледі:"
            if mode == "reexport"
            else f"🎨 30 кәсіби дизайн ішінен ұнағанын таңдаңыз\n(Қазіргі: {get_selected_theme_label(session.designId, session.pendingTopic)}):"
        )
        kb = build_clean_themes_keyboard(session, page, mode)
        if not is_doc:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
            )
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        return

    # Pick theme
    if data.startswith("pick_theme:"):
        theme_id = data.split(":")[1]
        session.designId = theme_id
        label = get_selected_theme_label(theme_id, session.pendingTopic)
        await callback.answer(f"✅ Таңдалды: {label}")

        if session.pendingTopic:
            text = build_topic_ready_text(session)
            kb = build_topic_ready_keyboard(session)
            if not is_doc:
                await bot.edit_message_text(
                    text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
                )
            else:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        elif not is_doc:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"✅ Дизайн сақталды: {label}\n📄 Бет саны: {session.slideCount} бет\n\nЕнді презентация тақырыбын жазыңыз!",
            )
        return

    # Instant Re-export
    if data.startswith("reexport_theme:"):
        theme_id = data.split(":")[1]
        session.designId = theme_id
        if not session.lastPresentation:
            await callback.answer("Алдымен тақырып жазып презентация жасап алыңыз.", show_alert=True)
            return

        res = reexport_deck_with_theme(session, theme_id, user_id=user_id)
        if not res:
            await callback.answer("Қате орын алды.")
            return

        pptx_bytes, filename, theme_name_kz = res
        await callback.answer(f"🎨 «{theme_name_kz}» дизайнымен жіберілуде...")
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

        caption = (
            f"🎨 <b>Жаңа дизайнмен дайын!</b>\n"
            f"📌 Тақырып: {session.lastPresentation.topic}\n"
            f"📄 Бет саны: {session.lastPresentation.slide_count} слайд\n"
            f"🎨 Дизайн: {theme_name_kz}\n\n"
            f"👇 PDF нұсқасы, Қорғау сөзі немесе басқа стиль таңдау:"
        )
        doc = BufferedInputFile(pptx_bytes, filename=filename)
        await bot.send_document(
            chat_id=chat_id,
            document=doc,
            caption=caption,
            reply_markup=dict_to_inline_markup(build_post_generation_keyboard(has_pdf=False)),
        )
        return

    # Back to topic
    if data == "back_to_topic":
        await callback.answer()
        text = build_topic_ready_text(session)
        kb = build_topic_ready_keyboard(session)
        if not is_doc:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
            )
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        return


async def main():
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment or .env file!")
        return

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Ботты іске қосу"),
                BotCommand(command="projects", description="📂 Менің жобаларым"),
                BotCommand(command="design", description="🎨 30 дизайн стилі"),
                BotCommand(command="slides", description="📄 Бет санын таңдау"),
                BotCommand(command="admin", description="📊 Әкімші статистикасы"),
                BotCommand(command="help", description="❓ Көмек және нұсқаулық"),
            ]
        )
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")

    logger.info("🤖 AI Presentation Telegram Bot (Aiogram 3) started successfully!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
