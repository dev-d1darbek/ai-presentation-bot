"""
Production AI Presentation Bot Pro v2 using Aiogram 3.
Complete Commercial Pro v2 Edition:
1. Instant 3-File Delivery (.PPTX + .PDF + .DOCX Defense Speech) with ONLY 2 buttons underneath ("🎨 Дизайнын ауыстыру" & "📄 Бет санын өзгерту")
2. 6 Tariffs & 3-Bucket Credit System ('no_photo_credits', 'ddg_photo_credits', 'openai_photo_credits' + 'bonus_credits'):
   - «Бір реттік» — 200 ₸ (1 фотосыз)
   - «Бір реттік + ФОТО» — 300 ₸ (1 интернеттен мысал фотомен + міндетті ескерту: ЖИ қателесуі мүмкін, PPTX-те өзі ауыстыра алады)
   - «Бір реттік + ФОТО (OpenAI)» — 500 ₸ (1 OpenAI gpt-image-2)
   - «Студент (Хит)» — 3,490 ₸ (20 през: 10 фотосыз + 5 фотомен + 5 OpenAI)
   - «Студент Pro» — 4,900 ₸ (30 през: 10 фотосыз + 10 фотомен + 10 OpenAI)
   - «Студент (VIP)» — 9,900 ₸ (80 през: 40 фотосыз + 20 фотомен + 20 OpenAI)
   - Тегін бонус тек «Бір реттік» және «Бір реттік + ФОТО» үшін ғана қолданылады; gpt-image-2 тек VIP/Pro/Хит/500₸ пакеттеріне рұқсат етіледі!
3. Admin Package CRUD: Админ жаңа пакеттер қоса алады, бағаларын өзгертеді, пакеттерді өшіре алады.
4. One-Time Promo Codes & Bonus Campaigns ('промокодтар тек Бір реттік істесін').
5. AI Cost Optimization (Негізгі AI: DeepSeek; Тегін қолданушылар: DeepSeek -> Fallback; Ақылы: DeepSeek -> Gemini -> OpenAI -> Fallback) & AI Cost Tracker.
6. 8 Specialized Templates + ҚР ЖОО ГОСТ 7.32-2017 Academic Standard.
7. Full Admin Control Center: 7d/30d Charts, Paginated & Filtered Users, 360° User History Card + Project Deletion, Segmented Broadcast, Manual Receipt Approval & CSV/Excel DB Export.
8. Viral Inline Mode (@your_bot тақырып).
"""
import asyncio
import base64
import hashlib
import io
import logging
import re
import time
from typing import Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
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
from config import is_admin
from app.core.themes import detect_best_theme_for_topic, THEMES_REGISTRY, get_selected_theme_label
from app.core.db import (
    log_user,
    get_user_profile,
    find_user_by_query,
    get_user_credits,
    get_user_credit_breakdown,
    consume_user_credit,
    add_user_credits,
    get_seller_setting,
    reset_seller_setting,
    get_kaspi_pay_url,
    set_kaspi_pay_url,
    get_dynamic_tariffs,
    update_tariff_setting,
    create_custom_tariff_package,
    delete_tariff_package,
    toggle_tariff_package,
    enable_all_tariff_packages,
    get_enabled_generation_modes,
    toggle_generation_mode,
    set_only_nophoto_mode,
    enable_all_generation_modes,
    create_payment_record,
    approve_payment,
    reject_payment,
    create_withdrawal_request,
    approve_withdrawal_request,
    reject_withdrawal_request,
    get_pending_withdrawals,
    get_recent_payments,
    get_all_user_ids,
    get_segmented_user_ids,
    get_users_paginated,
    get_user_projects,
    delete_user_project_by_id,
    apply_promo_code_to_user,
    create_or_update_promo_code,
    delete_promo_code,
    list_all_promo_codes,
    get_user_active_promo,
    get_ai_cost_stats,
    log_support_ticket,
    export_database_zip_bytes,
    track_funnel_event,
)
from app.core.redis_cache import redis_check_rate_limit
from app.core.verifier import (
    verify_kaspi_receipt,
    save_company_from_first_receipt,
    find_qr_url,
)
from app.core.doc_parser import extract_text_from_uploaded_file
from app.bot.session import get_telegram_session, save_session
from app.bot.keyboards.reply import get_persistent_reply_keyboard
from app.bot.keyboards.inline import (
    ensure_session_valid_mode,
    build_topic_ready_text,
    build_topic_ready_keyboard,
    build_templates_keyboard,
    build_clean_themes_keyboard,
    build_default_slides_keyboard,
    build_post_generation_keyboard,
    build_user_projects_keyboard,
    build_tariffs_keyboard,
    build_admin_payment_review_keyboard,
    build_admin_withdrawal_action_keyboard,
    build_admin_keyboard,
    build_admin_users_list_keyboard,
    build_admin_promos_keyboard,
    build_admin_broadcast_segment_keyboard,
    build_admin_kaspi_settings_keyboard,
    build_admin_price_editor_keyboard,
    build_admin_user_manage_keyboard,
    build_admin_reply_user_keyboard,
)
from app.bot.service import (
    parse_user_input,
    generate_deck_for_session,
    build_pdf_for_session,
    build_speech_for_session,
    reexport_deck_with_theme,
    load_saved_project_for_session,
    render_admin_analytics_chart_png,
    format_user_admin_card,
    format_admin_dashboard_text,
)
from app.bot.handlers.commands import (
    get_start_message,
    get_tariffs_message,
    get_payment_instruction_message,
    get_admin_kaspi_settings_message,
    get_admin_price_editor_message,
    get_admin_gen_modes_message,
    get_referral_message,
    get_support_message,
    get_help_message,
    get_slides_message,
    get_design_message,
    get_templates_message,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = Router()
BOT_USERNAME_CACHE: str = "ai_presentation_bot"

_user_last_gen: dict[int, float] = {}
RATE_LIMIT_SECONDS = 5


def is_rate_limited(user_id: int) -> bool:
    if is_admin(user_id):
        return False
    r_lim = redis_check_rate_limit(user_id, cooldown_seconds=RATE_LIMIT_SECONDS)
    if r_lim is not None:
        return r_lim
    now = time.time()
    last = _user_last_gen.get(user_id, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return True
    _user_last_gen[user_id] = now
    return False


class BotStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_withdrawal_amount = State()
    waiting_for_withdrawal_requisites = State()
    waiting_for_support_message = State()
    waiting_for_admin_reply = State()
    waiting_for_admin_user_search = State()
    waiting_for_kaspi_pay_url = State()
    waiting_for_tariff_price = State()
    waiting_for_new_package = State()
    waiting_for_promo_code = State()
    waiting_for_admin_new_promo = State()


def dict_to_inline_markup(d: dict) -> InlineKeyboardMarkup:
    rows = []
    for row in d.get("inline_keyboard", []):
        btn_row = []
        for btn in row:
            if "url" in btn:
                btn_row.append(InlineKeyboardButton(text=btn["text"], url=btn["url"]))
            else:
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


async def notify_referrer_bonuses(bot: Bot, reg_res: dict):
    ref_id = reg_res.get("referrer_id")
    if not ref_id:
        return

    inv_count = reg_res.get("referrer_invited_count", 0)
    if reg_res.get("free_slide_awarded"):
        try:
            await bot.send_message(
                chat_id=ref_id,
                text=(
                    f"🎉 <b>Құттықтаймыз!</b> Сіздің реферал сілтемеңіз арқылы <b>{inv_count} дос</b> қосылды!\n"
                    f"🎁 Сізге <b>+1 ТЕГІН презентация</b> («Бір реттік» немесе «Бір реттік + ФОТО» үшін) берілді!"
                ),
            )
        except Exception:
            pass

    partner_reward = reg_res.get("partner_reward_kzt", 0)
    if partner_reward > 0:
        try:
            await bot.send_message(
                chat_id=ref_id,
                text=(
                    f"💸 <b>СЕРІКТЕСТІК БОНУС ЕСЕПТЕЛДІ!</b>\n\n"
                    f"Сіз 20+ дос шақыру және 10 000 ₸ сатылым шартын орындадыңыз!\n"
                    f"💰 Серіктестік балансыңызға <b>+{partner_reward} ₸</b> қосылды!"
                ),
            )
        except Exception:
            pass


async def _animate_progress_bar(bot: Bot, chat_id: int, message_id: int, topic: str, count: int, theme_name: str, with_photos: bool):
    steps = [
        (30, "[▓▓▓░░░░░░░]", "📝 Слайдтар мазмұны мен құрылымы жазылуда..."),
        (60, "[▓▓▓▓▓▓░░░░]", "🖼 Фотосуреттер мен слайд дизайны құрастырылуда..." if with_photos else "🎨 Минималистік слайд блоктары мен инфографика жинақталуда..."),
        (85, "[▓▓▓▓▓▓▓▓░░]", "📑 Телефонға арналған .PDF және спикердің .DOCX Қорғау сөзі дайындалуда..."),
        (95, "[▓▓▓▓▓▓▓▓▓░]", "📦 3 дайын файл (.PPTX + .PDF + .DOCX) чатқа жүктелуде..."),
    ]
    try:
        for pct, bar, desc in steps:
            await asyncio.sleep(2.8)
            txt = (
                f"⏳ <b>«{topic}» дайындалуда...</b>\n\n"
                f"<code>{bar}</code> <b>{pct}%</b>\n"
                f"{desc}\n\n"
                f"📄 Көлемі: {count} слайд • 🎨 {theme_name}"
            )
            try:
                await bot.edit_message_text(text=txt, chat_id=chat_id, message_id=message_id)
            except Exception:
                pass
    except asyncio.CancelledError:
        pass


async def send_all_three_presentation_files(
    bot: Bot,
    chat_id: int,
    session,
    pptx_bytes: bytes,
    pptx_filename: str,
    theme_name_kz: str,
    rem_credits: int,
    from_cache: bool = False,
):
    """
    Бірден 3 дайын файлды жібереді:
    1. .PPTX презентация
    2. .PDF телефонда көру үшін
    3. .DOCX Қорғау сөзі (Шпаргалка)
    Астында ТЕК «🎨 Дизайнын ауыстыру» және «📄 Бет санын өзгерту» батырмалары тұрады!
    """
    pres = session.lastPresentation
    topic = pres.topic if pres else (session.pendingTopic or "Презентация")
    slide_cnt = pres.slide_count if pres else session.slideCount
    if pres and pres.with_photos:
        photo_badge = "✨ OpenAI Фото" if pres.image_source == "gpt-image-2" else "🖼 Фотомен (Интернет/ЖИ)"
    else:
        photo_badge = "🚫 Фотосыз (Минимализм)"
    speed_badge = "⚡ <i>Жылдам кэштен лезде дайындалды</i>\n" if from_cache else ""
    ddg_notice = (
        f"\n{config.DDG_PHOTO_WARNING_TEXT}\n"
        if (pres and pres.with_photos and pres.image_source != "gpt-image-2")
        else ""
    )

    # 1. Send .PPTX
    pptx_doc = BufferedInputFile(pptx_bytes, filename=pptx_filename)
    await bot.send_document(
        chat_id=chat_id,
        document=pptx_doc,
        caption=(
            f"📊 <b>1/3 • Негізгі презентация (.PPTX)</b>\n"
            f"{speed_badge}"
            f"📌 Тақырып: <b>{topic}</b>\n"
            f"📄 Көлемі: {slide_cnt} слайд • {photo_badge}\n"
            f"🎨 Дизайн: {theme_name_kz}{ddg_notice}"
        ),
    )

    # 2. Send .PDF
    pdf_res = build_pdf_for_session(session, pptx_bytes=None)
    if pdf_res:
        pdf_bytes, pdf_filename = pdf_res
        pdf_doc = BufferedInputFile(pdf_bytes, filename=pdf_filename)
        await bot.send_document(
            chat_id=chat_id,
            document=pdf_doc,
            caption=f"📱 <b>2/3 • Телефонда ашып көруге арналған нұсқа (.PDF)</b>\n📌 «{topic}» ({slide_cnt} бет)",
        )

    # 3. Send .DOCX + ONLY 2 buttons underneath!
    speech_res = build_speech_for_session(session)
    if speech_res:
        _full_text, docx_bytes, docx_filename = speech_res
        docx_doc = BufferedInputFile(docx_bytes, filename=docx_filename)
        await bot.send_document(
            chat_id=chat_id,
            document=docx_doc,
            caption=(
                f"🎤 <b>3/3 • Спикерге арналған Қорғау сөзі / Шпаргалка (.DOCX)</b>\n"
                f"🎫 Қалған жалпы лимит: <b>{rem_credits} презентация</b>\n\n"
                f"👇 Дизайнын немесе бет санын өзгерту:"
            ),
            reply_markup=dict_to_inline_markup(build_post_generation_keyboard()),
        )


async def execute_generation(
    bot: Bot,
    chat_id: int,
    session,
    user_id: Optional[int] = None,
    slide_count: Optional[int] = None,
    existing_msg_id: Optional[int] = None,
):
    uid = user_id or chat_id
    admin_flag = is_admin(uid)
    ensure_session_valid_mode(session)
    wants_photos = bool(session.withPhotos)
    img_src = session.imageSource or "ddg"

    if is_rate_limited(uid):
        await bot.send_message(
            chat_id=chat_id,
            text="⏳ Алдыңғы сұраныс орындалуда. Бірнеше секунд күте тұрыңыз.",
        )
        return

    # 1. АТОМДЫ ТҰТЫНУ — AI-ға ДЕЙІН
    # Ереже:
    # - Тегін бонус тек «Бір реттік» (фотосыз) және «Бір реттік + ФОТО» (ddg) үшін қолданылады.
    # - OpenAI gpt-image-2 тек VIP/Pro/Хит/500₸ пакетін алғандарға (openai_photo_credits > 0) рұқсат етіледі!
    if not admin_flag:
        if not consume_user_credit(uid, with_photos=wants_photos, image_source=img_src):
            b = get_user_credit_breakdown(uid)
            t_text, t_kb = get_tariffs_message(uid)
            if wants_photos and img_src == "gpt-image-2" and (b["bonus"] + b["ddg_photo"] + b["no_photo"]) > 0:
                t_kb_rows = [
                    [{"text": "🖼 «Бір реттік + ФОТО» (Интернет/ЖИ) режимімен жасау", "callback_data": f"gen_ddg_now:{slide_count or session.slideCount}"}],
                    [{"text": "🚫 «Бір реттік» (Фотосыз) режимімен жасау", "callback_data": f"gen_nophoto_now:{slide_count or session.slideCount}"}],
                ] + t_kb.get("inline_keyboard", [])
                msg = (
                    "✨ <b>OpenAI (<code>gpt-image-2</code>) фотогенерациясы — тек VIP / Pro / Хит немесе 500 ₸ OpenAI пакетінде қолжетімді!</b>\n\n"
                    f"💡 Сізде қазір <b>{b['bonus'] + b['ddg_photo'] + b['no_photo']} презентация</b> лимиті бар (Тегін бонус тек «Бір реттік» және «Бір реттік + ФОТО» үшін жарайды).\n"
                    "• Төмендегі батырмамен <b>«Бір реттік + ФОТО»</b> немесе <b>«Фотосыз»</b> режимінде дәл қазір жасай аласыз;\n"
                    "• Немесе OpenAI фотосы бар пакетті таңдаңыз:\n\n" + t_text
                )
                await bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    reply_markup=dict_to_inline_markup({"inline_keyboard": t_kb_rows}),
                )
                return

            if wants_photos and b["no_photo"] > 0 and b["ddg_photo"] == 0 and b["bonus"] == 0:
                t_kb_rows = [
                    [{"text": "🚫 Фотосыз лимитпен жасау", "callback_data": f"gen_nophoto_now:{slide_count or session.slideCount}"}],
                ] + t_kb.get("inline_keyboard", [])
                msg = (
                    f"⚠️ <b>Сізде фотомен жасау лимиті қалмады, бірақ {b['no_photo']} фотосыз презентация бар!</b>\n\n"
                    "Төмендегі батырмамен фотосыз жасаңыз немесе фото-пакет алыңыз:\n\n" + t_text
                )
                await bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    reply_markup=dict_to_inline_markup({"inline_keyboard": t_kb_rows}),
                )
                return

            msg = (
                "⚠️ <b>Балансыңызда презентация қалмады (0).</b>\n\n"
                "Жаңа презентация үшін пакет таңдаңыз немесе "
                "<b>2 дос шақырып +1 тегін презентация</b> алыңыз!\n\n" + t_text
            )
            if existing_msg_id:
                try:
                    await bot.edit_message_text(
                        text=msg,
                        chat_id=chat_id,
                        message_id=existing_msg_id,
                        reply_markup=dict_to_inline_markup(t_kb),
                    )
                    return
                except Exception:
                    pass
            await bot.send_message(chat_id=chat_id, text=msg, reply_markup=dict_to_inline_markup(t_kb))
            return

    topic = session.pendingTopic or (
        session.lastPresentation.topic if session.lastPresentation else "Жасанды интеллект"
    )
    count = slide_count or session.slideCount
    selected_theme = (
        THEMES_REGISTRY[session.designId]
        if session.designId != "auto" and session.designId in THEMES_REGISTRY
        else detect_best_theme_for_topic(topic, with_photos=wants_photos)
    )

    track_funnel_event(uid, "generation_started", {"topic": topic, "slides": count, "with_photos": wants_photos})

    ddg_warn_line = f"\n\n{config.DDG_PHOTO_WARNING_TEXT}" if (wants_photos and img_src == "ddg") else ""
    status_text = (
        f"⏳ <b>«{topic}» дайындалуда...</b>\n\n"
        f"<code>[▓░░░░░░░░░]</code> <b>10%</b>\n"
        f"🧠 Тақырып талданып, презентация құрылымы құрылуда...\n\n"
        f"📄 Көлемі: {count} слайд • 🎨 {selected_theme.nameKz}{ddg_warn_line}"
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

    progress_task = None
    if status_msg_id:
        progress_task = asyncio.create_task(
            _animate_progress_bar(bot, chat_id, status_msg_id, topic, count, selected_theme.nameKz, wants_photos)
        )

    try:
        pptx_bytes, filename, presentation, from_cache = await generate_deck_for_session(
            session, user_id=uid, slide_count=count
        )
        if progress_task:
            progress_task.cancel()

        save_session(chat_id, session)
        rem_credits = get_user_credits(uid)

        await send_all_three_presentation_files(
            bot=bot,
            chat_id=chat_id,
            session=session,
            pptx_bytes=pptx_bytes,
            pptx_filename=filename,
            theme_name_kz=selected_theme.nameKz,
            rem_credits=rem_credits,
            from_cache=from_cache,
        )

        if status_msg_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
            except Exception:
                pass
    except Exception as e:
        if progress_task:
            progress_task.cancel()
        if not admin_flag:
            if wants_photos and img_src == "gpt-image-2":
                add_user_credits(uid, 1, no_photo_to_add=0, openai_photo_to_add=1)
            elif wants_photos:
                add_user_credits(uid, 1, is_bonus=True)
            else:
                add_user_credits(uid, 1, is_bonus=True)
        logger.error(f"Generation error (credit refunded): {e}", exc_info=True)
        await bot.send_message(
            chat_id=chat_id,
            text="❌ Қате орын алды. Лимитіңіз сақталды — қайта көріңіз.",
        )


# ----------------- Viral Inline Mode (@your_bot тақырып) -----------------

@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery):
    """
    Вирустық маркетингке арналған Инлайн-режим:
    Кез келген чатта @bot_username тақырып деп жазғанда дайын карточкалар шығарады.
    """
    query_text = (inline_query.query or "").strip()
    topic = query_text if len(query_text) >= 2 else "Қазақстан тарихы"
    clean_bot = BOT_USERNAME_CACHE.lstrip("@") or "ai_presentation_bot"

    enc_topic = base64.urlsafe_b64encode(topic[:42].encode("utf-8")).decode("ascii").rstrip("=")
    deep_link = f"https://t.me/{clean_bot}?start=inl_{enc_topic}"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🚀 «{topic[:24]}» презентациясын алу (.PPTX+.PDF+.DOCX)", url=deep_link)],
        ]
    )

    results = [
        InlineQueryResultArticle(
            id=hashlib.md5(f"std_{topic}".encode("utf-8")).hexdigest(),
            title=f"📊 Презентация жасау: «{topic}»",
            description="Бірден 3 файл (.PPTX + .PDF + .DOCX Қорғау сөзі) • Жоғары сапалы дизайн",
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"📊 <b>«{topic}»</b> тақырыбына дайын презентация (.PPTX + .PDF) және Қорғау сөзі (.DOCX)!\n\n"
                    f""
                    f"🎁 Жаңа қолданушыларға <b>1 презентация ТЕГІН</b> беріледі!\n\n"
                    f"👇 Төмендегі батырманы басып, презентацияны жүктеп алыңыз:"
                ),
                parse_mode=ParseMode.HTML,
            ),
            reply_markup=kb,
        ),
        InlineQueryResultArticle(
            id=hashlib.md5(f"photo_{topic}".encode("utf-8")).hexdigest(),
            title=f"🖼 ВАУ Фото-Презентация: «{topic}»",
            description="Иллюстрациялық фотолармен + 35 эксклюзивті дизайн + Қорғау сөзі",
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"🖼 <b>«{topic}»</b> — Фотосуреттері бар журнал стиліндегі ВАУ презентация (.PPTX + .PDF + .DOCX)!\n\n"
                    f"👇 Дайын презентацияны алу үшін батырманы басыңыз:"
                ),
                parse_mode=ParseMode.HTML,
            ),
            reply_markup=kb,
        ),
    ]
    await inline_query.answer(results, cache_time=5, is_personal=True)


# ----------------- Command & Main Menu Handlers -----------------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    uid = message.from_user.id if message.from_user else message.chat.id
    referrer_id = None
    promo_arg = None
    inline_topic = None

    parts = (message.text or "").split()
    if len(parts) > 1:
        arg = parts[1].strip()
        if arg.startswith("ref_"):
            ref_str = arg.replace("ref_", "").strip()
            if ref_str.isdigit():
                referrer_id = int(ref_str)
        elif arg.startswith("promo_"):
            promo_arg = arg.replace("promo_", "").strip()
        elif arg.startswith("inl_"):
            b64_part = arg.replace("inl_", "").strip()
            pad = "=" * ((4 - len(b64_part) % 4) % 4)
            try:
                inline_topic = base64.urlsafe_b64decode(b64_part + pad).decode("utf-8", errors="ignore")
            except Exception:
                pass

    reg_res = {"is_new": False, "streak_days": 1, "streak_bonus_awarded": False}
    if message.from_user:
        reg_res = log_user(
            uid,
            message.from_user.username,
            message.from_user.first_name,
            referrer_id=referrer_id,
        )
        await notify_referrer_bonuses(bot, reg_res)

    track_funnel_event(uid, "start", {"is_new": reg_res.get("is_new", False)})

    if promo_arg:
        ok, p_msg, _ = apply_promo_code_to_user(uid, promo_arg)
        await message.answer(p_msg)

    if inline_topic:
        session = get_telegram_session(message.chat.id)
        session.pendingTopic = inline_topic
        save_session(message.chat.id, session)
        card_text = build_topic_ready_text(session, user_id=uid)
        card_kb = build_topic_ready_keyboard(session)
        await message.answer(card_text, reply_markup=dict_to_inline_markup(card_kb))
        return

    text, kb = get_start_message(
        message.chat.id,
        is_new=reg_res.get("is_new", False),
        streak_days=reg_res.get("streak_days", 1),
        streak_bonus=reg_res.get("streak_bonus_awarded", False),
    )
    await message.answer(text, reply_markup=dict_to_reply_markup(kb))


@router.message(Command("templates"))
@router.message(F.text.in_({"📐 Үлгілер (ГОСТ / Шаблон)", "📐 Үлгілер (Шаблон)"}))
async def cmd_templates(message: Message, state: FSMContext):
    await state.clear()
    text, kb = get_templates_message(message.chat.id)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


@router.message(Command("promo"))
async def cmd_promo(message: Message):
    uid = message.from_user.id if message.from_user else message.chat.id
    parts = (message.text or "").split()

    if len(parts) >= 3 and is_admin(uid) and parts[2].isdigit():
        code = parts[1].strip().upper()
        pct = int(parts[2])
        desc = " ".join(parts[3:]) if len(parts) > 3 else f"{code} — {pct}% жеңілдік"
        created = create_or_update_promo_code(code, pct, desc)
        await message.answer(
            f"✅ <b>Промокод сақталды!</b>\n"
            f"🎟 Код: <code>{created['code']}</code>\n"
            f"🏷 Жеңілдік: <b>-{created['discount_percent']}%</b>\n"
            f"📝 Сипаттамасы: {created['description']}"
        )
        return

    if len(parts) >= 2:
        code = parts[1].strip()
        ok, msg_text, _ = apply_promo_code_to_user(uid, code)
        t_text, t_kb = get_tariffs_message(uid)
        await message.answer(f"{msg_text}\n\n{t_text}", reply_markup=dict_to_inline_markup(t_kb))
        return

    await message.answer(
        "🎟 <b>1-реттік Промокод немесе Сыйлық науқанын белсендіру:</b>\n\n"
        "• Науқандық жеңілдік: <code>/promo ALASH2025</code> (-50%)\n"
        "• ҚазҰУ студенттеріне: <code>/promo KAZNU50</code> (-50%)\n"
        "• ЕҰУ студенттеріне: <code>/promo ENU50</code> (-50%)\n"
        "• Сыйлық науқаны: <code>/promo BONUS2025</code> (+1 тегін през)"
    )


@router.message(Command("status"))
async def cmd_status(message: Message):
    seller = get_seller_setting()
    pay_url = get_kaspi_pay_url()
    if not seller:
        await message.answer(
            "ℹ️ <b>Компания әлі сақталмаған.</b>\n"
            "📄 Алғашқы Kaspi Pay PDF чегін жіберіңіз — бот компанияны (атауы мен ЖСН/БСН) автоматты түрде есте сақтайды."
        )
        return
    await message.answer(
        "🏢 <b>Сақталған компания</b>\n\n"
        f"Атауы: <b>{seller.get('company')}</b>\n"
        f"ЖСН/БСН: <code>{seller.get('company_bin')}</code>\n"
        f"Үлгі чек: <code>{seller.get('sample_receipt') or '—'}</code>\n"
        f"Kaspi Pay: <code>{pay_url}</code>"
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    uid = message.from_user.id if message.from_user else 0
    if not is_admin(uid):
        await message.answer("⛔️ Бұл команда тек әкімшіге арналған.")
        return
    reset_seller_setting()
    await message.answer(
        "✅ <b>Компания тазаланды.</b>\n"
        "Енді жаңа Kaspi Pay-дің алғашқы PDF чегін жіберіңіз — бот жаңа компания мен ЖСН/БСН-ды автоматты түрде орнатады!"
    )


@router.message(Command("tariffs"))
@router.message(Command("balance"))
@router.message(F.text.in_({"💳 Баланс / Тарифтер", "💳 Тарифтер"}))
async def cmd_tariffs(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id if message.from_user else message.chat.id
    track_funnel_event(uid, "tariff_viewed")
    text, kb = get_tariffs_message(uid)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


@router.message(Command("referral"))
@router.message(F.text.in_({"👥 Реферал (Табыс табу)", "👥 Реферал"}))
async def cmd_referral(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    global BOT_USERNAME_CACHE
    try:
        me = await bot.get_me()
        if me.username:
            BOT_USERNAME_CACHE = me.username
    except Exception:
        pass
    uid = message.from_user.id if message.from_user else message.chat.id
    text, kb = get_referral_message(uid, BOT_USERNAME_CACHE)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


@router.message(Command("support"))
@router.message(F.text.in_({"👨‍💻 Админмен байланыс", "❓ Көмек"}))
async def cmd_support(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id if message.from_user else message.chat.id
    if message.text == "❓ Көмек":
        text, kb = get_help_message()
        await message.answer(text, reply_markup=dict_to_reply_markup(kb))
        return
    text, kb = get_support_message(uid)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    text, kb = get_help_message()
    await message.answer(text, reply_markup=dict_to_reply_markup(kb))


@router.message(Command("slides"))
@router.message(F.text.in_({"📄 Бет саны", "📄 Бет санын таңдау"}))
async def cmd_slides(message: Message, state: FSMContext):
    await state.clear()
    text, kb = get_slides_message(message.chat.id)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


@router.message(Command("design"))
@router.message(F.text.in_({"🎨 Дизайн таңдау", "🎨 Дизайн таңдау (30 стиль)"}))
async def cmd_design(message: Message, state: FSMContext):
    await state.clear()
    text, kb = get_design_message(message.chat.id)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


@router.message(Command("projects"))
@router.message(F.text == "📂 Менің жобаларым")
async def cmd_projects(message: Message, state: FSMContext):
    await state.clear()
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
        f"Кез келген жобаны бассаңыз, бот бірден <b>.PPTX + .PDF + .DOCX Қорғау сөзін</b> қайта жібереді:"
    )
    kb = build_user_projects_keyboard(projects, page=0, total_count=total)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


# ----------------- Admin Commands (/admin and /give) -----------------

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id if message.from_user else 0
    if not is_admin(user_id):
        await message.answer("⛔️ Бұл команда тек әкімшіге арналған.")
        return

    text, pend_w, pend_p = format_admin_dashboard_text()
    await message.answer(text, reply_markup=dict_to_inline_markup(build_admin_keyboard(pend_w, pend_p)))


@router.message(Command("give"))
async def cmd_give(message: Message, bot: Bot):
    admin_id = message.from_user.id if message.from_user else 0
    if not is_admin(admin_id):
        await message.answer("⛔️ Бұл команда тек әкімшіге арналған.")
        return

    parts = (message.text or "").split()
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer(
            "ℹ️ <b>Қолдану үлгісі:</b>\n"
            "<code>/give USER_ID САНЫ_НЕМЕСЕ_ПАКЕТ</code>\n\n"
            "Мысалы:\n"
            "• <code>/give 1234567 5</code> — 5 бонус презентация қосу\n"
            "• <code>/give 1234567 hit</code> — Хит пакетін қосу (10 фотосыз + 5 фото + 5 OpenAI)\n"
            "• <code>/give 1234567 pro</code> — Студент Pro пакетін қосу (10+10+10)\n"
            "• <code>/give 1234567 vip</code> — VIP пакетін қосу (40+20+20)"
        )
        return

    target_uid = int(parts[1])
    raw_val = parts[2].lower().strip()
    tariffs = get_dynamic_tariffs()
    if raw_val in tariffs:
        t = tariffs[raw_val]
        credits_to_give = int(t["credits"])
        np_add = int(t.get("no_photo_credits", 0))
        ddg_add = int(t.get("ddg_photo_credits", 0))
        oai_add = int(t.get("openai_photo_credits", 0))
        new_bal = add_user_credits(
            target_uid, credits_to_give,
            no_photo_to_add=np_add, ddg_photo_to_add=ddg_add, openai_photo_to_add=oai_add,
        )
    elif raw_val.lstrip("-").isdigit():
        credits_to_give = int(raw_val)
        new_bal = add_user_credits(target_uid, credits_to_give, is_bonus=(credits_to_give > 0))
    else:
        await message.answer("⚠️ Қате мән. Сан жазыңыз немесе <code>hit</code> / <code>pro</code> / <code>vip</code> деп көрсетіңіз.")
        return

    await message.answer(
        f"✅ Пайдаланушыға (ID: <code>{target_uid}</code>) <b>{credits_to_give:+d} презентация</b> жазылды!\n"
        f"🎫 Жаңа балансы: <b>{new_bal} презентация</b>."
    )

    if credits_to_give > 0:
        try:
            await bot.send_message(
                chat_id=target_uid,
                text=(
                    f"🎁 <b>Құттықтаймыз!</b>\n"
                    f"Әкімші сіздің балансыңызға <b>+{credits_to_give} презентация</b> қосты!\n"
                    f"🎫 Қазіргі балансыңыз: <b>{new_bal} презентация</b>."
                ),
            )
        except Exception:
            pass


# ----------------- FSM States: Promo, Packages CRUD, Broadcast, Withdrawals, Support -----------------

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Әрекет тоқтатылды.", reply_markup=dict_to_reply_markup(get_persistent_reply_keyboard()))


@router.callback_query(F.data == "enter_promo")
async def cb_enter_promo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_promo_code)
    await callback.message.answer(
        "🎟 <b>1-реттік Промокодты немесе Сыйлық науқаны кодын жазып жіберіңіз:</b>\n"
        "Мысалы: <code>ALASH2025</code>, <code>KAZNU50</code> (-50%) немесе <code>BONUS2025</code> (+1 тегін през)\n\n"
        "Бас тарту үшін: /cancel"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_promo_code)
async def process_promo_code_input(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id if message.from_user else message.chat.id
    code = (message.text or "").strip()
    ok, msg_text, _ = apply_promo_code_to_user(uid, code)
    t_text, t_kb = get_tariffs_message(uid)
    await message.answer(f"{msg_text}\n\n{t_text}", reply_markup=dict_to_inline_markup(t_kb))


@router.callback_query(F.data == "adm_add_promo")
async def cb_adm_add_promo(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return
    await state.set_state(BotStates.waiting_for_admin_new_promo)
    await callback.message.answer(
        "🎟 <b>Жаңа Промокод немесе Сыйлық Науқанын қосу:</b>\n\n"
        "Формат:\n"
        "• Жеңілдік промокоды үшін: <code>КОД ПАЙЫЗ</code> (мысалы: <code>KBTU50 50</code>)\n"
        "• Тегін презентация беретін Сыйлық науқаны үшін: <code>КОД bonus САНЫ</code> (мысалы: <code>NAURYZ bonus 2</code>)\n\n"
        "Бас тарту үшін: /cancel"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_admin_new_promo)
async def process_admin_new_promo(message: Message, state: FSMContext):
    await state.clear()
    parts = (message.text or "").strip().split()
    if len(parts) < 2:
        await message.answer("⚠️ Қате формат. Мысалы: <code>KBTU50 50</code> немесе <code>GIFT2025 bonus 1</code>")
        return

    code = parts[0].upper()
    if len(parts) >= 3 and parts[1].lower() == "bonus" and parts[2].isdigit():
        b_cnt = int(parts[2])
        create_or_update_promo_code(code, discount_percent=0, bonus_credits=b_cnt, description=f"+{b_cnt} тегін презентация")
    elif parts[1].isdigit():
        pct = int(parts[1])
        create_or_update_promo_code(code, discount_percent=pct, bonus_credits=0)
    else:
        await message.answer("⚠️ Қате мән.")
        return

    promos = list_all_promo_codes()
    await message.answer(
        f"✅ <b>«{code}» промокоды/науқаны қосылды!</b>",
        reply_markup=dict_to_inline_markup(build_admin_promos_keyboard(promos)),
    )


@router.callback_query(F.data == "adm_add_pkg")
async def cb_adm_add_pkg(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return
    await state.set_state(BotStates.waiting_for_new_package)
    await callback.message.answer(
        "➕ <b>Жаңа Тарифтік Пакет Қосу</b>\n\n"
        "Формат (үтір немесе вертикал сызық <code>|</code> арқылы):\n"
        "<code>Атауы | Бағасы | Фотосыз_саны | Фото_саны | OpenAI_саны</code>\n\n"
        "Мысалы:\n"
        "<code>Магистрант Pro | 6900 | 20 | 15 | 15</code>\n\n"
        "Бас тарту үшін: /cancel"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_new_package)
async def process_admin_new_package(message: Message, state: FSMContext):
    await state.clear()
    raw = (message.text or "").strip()
    parts = [p.strip() for p in re.split(r"[|,]", raw) if p.strip()]
    if len(parts) < 3:
        await message.answer("⚠️ Қате формат. Мысалы: <code>Магистрант Pro | 6900 | 20 | 15 | 15</code>")
        return

    title = parts[0]
    nums = [int(re.sub(r"[^\d]", "", x) or "0") for x in parts[1:]]
    price = max(100, nums[0])
    np_c = nums[1] if len(nums) > 1 else 10
    ddg_c = nums[2] if len(nums) > 2 else 0
    oai_c = nums[3] if len(nums) > 3 else 0

    created = create_custom_tariff_package(title, price, np_c, ddg_c, oai_c)
    text, kb = get_admin_price_editor_message()
    await message.answer(
        f"✅ <b>Жаңа пакет қосылды: {created['title']} — {created['price_kzt']:,} ₸ ({created['credits']} през)!</b>\n\n{text}",
        reply_markup=dict_to_inline_markup(kb),
    )


@router.callback_query(F.data == "admin_set_pay_url")
async def cb_admin_set_pay_url(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return

    await state.set_state(BotStates.waiting_for_kaspi_pay_url)
    await callback.message.answer(
        "🔗 <b>Жаңа Kaspi Pay төлем сілтемесін жіберіңіз</b>\n"
        "(мысалы: <code>https://pay.kaspi.kz/pay/...</code>) немесе бас тарту үшін /cancel:"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_kaspi_pay_url)
async def process_new_kaspi_pay_url(message: Message, state: FSMContext):
    await state.clear()
    url = (message.text or "").strip()
    if not url.startswith("http"):
        await message.answer("⚠️ Қате сілтеме. Сілтеме <code>https://</code> деп басталуы керек.")
        return

    set_kaspi_pay_url(url)
    text, kb = get_admin_kaspi_settings_message()
    await message.answer(
        f"✅ <b>Kaspi Pay сілтемесі сәтті жаңартылды!</b>\n\n{text}",
        reply_markup=dict_to_inline_markup(kb),
    )


@router.callback_query(F.data.startswith("edit_tariff:"))
async def cb_edit_tariff(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return

    tariff_id = callback.data.split(":")[1]
    tariffs = get_dynamic_tariffs(include_disabled=True)
    t = tariffs.get(tariff_id, next(iter(tariffs.values())))

    await state.update_data(edit_tariff_id=tariff_id)
    await state.set_state(BotStates.waiting_for_tariff_price)
    await callback.message.answer(
        f"✏️ <b>{t['title']} пакетін өзгерту</b>\n"
        f"Қазіргі бағасы: <b>{t['price_kzt']:,} ₸</b> ({t.get('no_photo_credits', 0)} фотосыз / {t.get('ddg_photo_credits', 0)} фото / {t.get('openai_photo_credits', 0)} OpenAI)\n\n"
        f"💵 <b>Жаңа бағаны жазыңыз:</b>\n"
        f"• Тек бағаны өзгерту: мысалы <code>{t['price_kzt']}</code>\n"
        f"• Баға мен 3 лимитті бірге өзгерту (Баға Фотосыз Фото OpenAI): мысалы <code>4900 10 10 10</code>\n\n"
        f"Бас тарту үшін: /cancel"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_tariff_price)
async def process_new_tariff_price(message: Message, state: FSMContext):
    data = await state.get_data()
    tariff_id = data.get("edit_tariff_id", "hit")
    await state.clear()

    nums = [int(x) for x in re.findall(r"\d+", message.text or "")]
    if not nums or nums[0] <= 0:
        await message.answer("⚠️ Қате мән. Жаңа бағаны санмен жазыңыз.")
        return

    new_price = nums[0]
    if len(nums) >= 4:
        updated = update_tariff_setting(
            tariff_id, price_kzt=new_price,
            no_photo_credits=nums[1], ddg_photo_credits=nums[2], openai_photo_credits=nums[3],
        )
    elif len(nums) == 2:
        updated = update_tariff_setting(tariff_id, price_kzt=new_price, credits=nums[1])
    else:
        updated = update_tariff_setting(tariff_id, price_kzt=new_price)

    text, kb = get_admin_price_editor_message()
    await message.answer(
        f"✅ <b>{updated['title']} жаңартылды: {updated['price_kzt']:,} ₸ ({updated['credits']} през)!</b>\n\n{text}",
        reply_markup=dict_to_inline_markup(kb),
    )


@router.callback_query(F.data == "withdraw_partner")
async def cb_withdraw_partner(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    profile = get_user_profile(uid)
    bal = int(profile.get("partner_balance_kzt", 0))

    if bal < config.MIN_WITHDRAWAL_KZT:
        await callback.answer(
            f"⚠️ Шығарудың минималды құны — {config.MIN_WITHDRAWAL_KZT} ₸. Қазіргі балансыңыз: {bal} ₸.",
            show_alert=True,
        )
        return

    await state.set_state(BotStates.waiting_for_withdrawal_amount)
    await callback.message.answer(
        f"💸 <b>Серіктестік табысты шығару</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Қолжетімді балансыңыз: <b>{bal:,} ₸</b>\n"
        f"📉 Минималды шығару сомасы: <b>{config.MIN_WITHDRAWAL_KZT:,} ₸</b>\n\n"
        f"💵 <b>Қанша теңге шығарғыңыз келеді?</b> Соманы санмен жазыңыз (мысалы: <code>{bal}</code>) "
        f"немесе бас тарту үшін /cancel басыңыз:"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_withdrawal_amount)
async def process_withdrawal_amount(message: Message, state: FSMContext):
    uid = message.from_user.id if message.from_user else message.chat.id
    profile = get_user_profile(uid)
    bal = int(profile.get("partner_balance_kzt", 0))

    raw = re.sub(r"[^\d]", "", (message.text or ""))
    if not raw.isdigit():
        await message.answer("⚠️ Тек санмен жазыңыз (мысалы: <code>2000</code>) немесе /cancel:")
        return

    amount = int(raw)
    if amount < config.MIN_WITHDRAWAL_KZT:
        await message.answer(
            f"⚠️ Минималды шығару сомасы — <b>{config.MIN_WITHDRAWAL_KZT} ₸</b>. "
            f"Кемінде {config.MIN_WITHDRAWAL_KZT} ₸ жазыңыз:"
        )
        return

    if amount > bal:
        await message.answer(
            f"⚠️ Сіздің қолжетімді балансыңыз — <b>{bal} ₸</b>. Одан көп сома жазу мүмкін емес. Қайта жазыңыз:"
        )
        return

    await state.update_data(withdraw_amount=amount)
    await state.set_state(BotStates.waiting_for_withdrawal_requisites)
    await message.answer(
        f"💳 <b>{amount:,} ₸</b> аударылатын <b>Kaspi телефон нөміріңізді</b> немесе "
        f"<b>16 таңбалы карта нөміріңізді</b> (және аты-жөніңізді) жазыңыз:\n\n"
        f"<i>Мысалы: +7 777 123 45 67 Айдос С. немесе 4400 4301 1234 5678</i>"
    )


@router.message(BotStates.waiting_for_withdrawal_requisites)
async def process_withdrawal_requisites(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    amount = int(data.get("withdraw_amount", config.MIN_WITHDRAWAL_KZT))
    await state.clear()

    uid = message.from_user.id if message.from_user else message.chat.id
    requisites = (message.text or "").strip()
    if len(requisites) < 5:
        await message.answer("⚠️ Реквизит тым қысқа. Қайтадан «👥 Реферал» мәзірінен сұраныс жіберіңіз.")
        return

    w_id, err = create_withdrawal_request(uid, amount, requisites)
    if err or not w_id:
        await message.answer(err or "❌ Сұраныс жасау мүмкін болмады.")
        return

    profile = get_user_profile(uid)
    await message.answer(
        f"✅ <b>Шығару сұранысы (#{w_id}) әкімшіге жіберілді!</b>\n\n"
        f"💵 Сомасы: <b>{amount:,} ₸</b>\n"
        f"💳 Реквизит: <code>{requisites}</code>\n\n"
        f"Әкімші төлем жасаған сәтте сізге хабарлама келеді.",
        reply_markup=dict_to_reply_markup(get_persistent_reply_keyboard()),
    )

    u_tag = f"@{message.from_user.username}" if (message.from_user and message.from_user.username) else str(uid)
    adm_kb = dict_to_inline_markup(build_admin_withdrawal_action_keyboard(w_id, amount))
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💸 <b>ЖАҢА ТӨЛЕМ ШЫҒАРУ СҰРАНЫСЫ (#{w_id})</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 Студент: {u_tag} (ID: <code>{uid}</code>)\n"
                    f"💵 <b>Сұраған сомасы: {amount:,} ₸</b>\n"
                    f"💳 <b>Kaspi / Карта:</b> <code>{requisites}</code>"
                ),
                reply_markup=adm_kb,
            )
        except Exception:
            pass


@router.callback_query(F.data == "start_support_msg")
async def cb_start_support_msg(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_support_message)
    await callback.message.answer(
        "✍️ <b>Әкімшіге жазатын сұрағыңызды немесе шағымыңызды осында жазып жіберіңіз</b> "
        "(бас тарту үшін /cancel):"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_support_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    uid = message.from_user.id if message.from_user else message.chat.id
    u_tag = f"@{message.from_user.username}" if (message.from_user and message.from_user.username) else "Жоқ"
    fname = message.from_user.first_name if message.from_user else "Қолданушы"
    text = (message.text or "").strip()

    log_support_ticket(uid, text)

    await message.answer(
        "✅ <b>Хабарламаңыз әкімшіге жеткізілді!</b> Жауабы осы чатқа келеді.",
        reply_markup=dict_to_reply_markup(get_persistent_reply_keyboard()),
    )

    adm_kb = dict_to_inline_markup(build_admin_reply_user_keyboard(uid))
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f"📩 <b>ҚОЛДАНУШЫДАН ХАБАРЛАМА / ШАҒЫМ</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 Аты: <b>{fname}</b> ({u_tag})\n"
                    f"🆔 ID: <code>{uid}</code>\n\n"
                    f"💬 <b>Мәтіні:</b>\n{text}"
                ),
                reply_markup=adm_kb,
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("reply_user:"))
async def cb_reply_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return

    target_uid = int(callback.data.split(":")[1])
    await state.update_data(reply_target_uid=target_uid)
    await state.set_state(BotStates.waiting_for_admin_reply)
    await callback.message.answer(
        f"💬 Пайдаланушыға (ID: <code>{target_uid}</code>) жіберілетін жауап мәтінін жазыңыз (немесе /cancel):"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_admin_reply)
async def process_admin_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target_uid = data.get("reply_target_uid")
    await state.clear()

    if not target_uid:
        await message.answer("❌ Қате: алушы ID табылмады.")
        return

    reply_text = (message.text or "").strip()
    try:
        await bot.send_message(
            chat_id=target_uid,
            text=(
                f"👨‍💻 <b>Бот әкімшісінен жауап:</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{reply_text}"
            ),
            reply_markup=dict_to_inline_markup(
                {"inline_keyboard": [[{"text": "✍️ Қайта жауап жазу", "callback_data": "start_support_msg"}]]}
            ),
        )
        await message.answer(f"✅ Жауабыңыз <code>{target_uid}</code> қолданушысына жеткізілді!")
    except Exception as e:
        await message.answer(f"❌ Хабарлама жіберу мүмкін болмады: {e}")


@router.callback_query(F.data == "admin_find_user")
async def cb_admin_find_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return

    await state.set_state(BotStates.waiting_for_admin_user_search)
    await callback.message.answer(
        "🔍 Іздегіңіз келетін қолданушының <b>Telegram ID</b> нөмірін немесе <b>@username</b> атын жазыңыз (немесе /cancel):"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_admin_user_search)
async def process_admin_user_search(message: Message, state: FSMContext):
    await state.clear()
    query = (message.text or "").strip()
    prof = find_user_by_query(query)
    if not prof:
        await message.answer(f"❌ <code>{query}</code> бойынша қолданушы табылмады.")
        return

    card_text, projects = format_user_admin_card(prof["user_id"])
    kb = dict_to_inline_markup(build_admin_user_manage_keyboard(prof["user_id"], projects=projects))
    await message.answer(card_text, reply_markup=kb)


@router.callback_query(F.data.startswith("adm_bcast_seg:"))
async def cb_admin_broadcast_seg(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return

    seg = callback.data.split(":")[1]
    target_ids = get_segmented_user_ids(seg)
    seg_names = {
        "all": "Барлық қолданушылар",
        "vip_paid": "Тек VIP / Pro (Төлем жасағандар)",
        "photo_users": "Тек Фотомен жасағандар",
        "active_7d": "Соңғы 7 күнде белсенділер",
    }
    await state.update_data(broadcast_segment=seg)
    await state.set_state(BotStates.waiting_for_broadcast)
    await callback.message.answer(
        f"📢 <b>Сегмент: {seg_names.get(seg, seg)} ({len(target_ids)} адам)</b>\n\n"
        f"Тарататын хабарлама мәтінін жазыңыз (немесе бас тарту үшін /cancel):"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    seg = data.get("broadcast_segment", "all")
    await state.clear()

    text = message.text
    user_ids = get_segmented_user_ids(seg)
    sent_count = 0

    await message.answer(f"⏳ {len(user_ids)} пайдаланушыға ({seg}) тарату басталды...")
    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=text)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.answer(f"✅ Хабарлама {sent_count}/{len(user_ids)} адамға сәтті жеткізілді!")


# ----------------- Kaspi Pay Receipt Auto-Setup, Auto-Verification & Manual Approval Fallback -----------------

async def process_kaspi_receipt_upload(
    message: Message,
    bot: Bot,
    file_bytes: bytes,
    filename: str,
    session,
):
    uid = message.from_user.id if message.from_user else message.chat.id
    u_tag = f"@{message.from_user.username}" if (message.from_user and message.from_user.username) else str(uid)

    ver_msg = await message.answer("🔎 <b>Чек тексерілуде...</b>")

    seller = get_seller_setting()
    if not seller:
        ok, setup_msg, _ = save_company_from_first_receipt(uid, file_bytes)
        await ver_msg.edit_text(setup_msg)
        return

    ver_res = verify_kaspi_receipt(
        file_bytes=file_bytes,
        filename=filename,
        expected_tariff_id=session.pendingTariffId,
        user_id=uid,
    )

    if ver_res.is_duplicate:
        await ver_msg.edit_text(ver_res.reason)
        return

    tariffs = get_dynamic_tariffs(user_id=uid)
    tariff_id = ver_res.matched_tariff_id or session.pendingTariffId or "single"
    tariff = tariffs.get(tariff_id, next(iter(tariffs.values())))
    active_promo = get_user_active_promo(uid)

    # If auto-verification could not confirm QR/Kaspi online -> create pending record for Manual Admin Approval!
    if not ver_res.is_valid:
        if ver_res.needs_manual_review and config.ADMIN_IDS:
            pend_id = create_payment_record(
                user_id=uid,
                tariff_id=tariff_id,
                amount_kzt=int(tariff["price_kzt"]),
                credits_added=int(tariff["credits"]),
                receipt_hash=ver_res.receipt_hash,
                receipt_number=ver_res.receipt_number or f"MANUAL_{int(time.time())}",
                status="pending",
                no_photo_added=int(tariff.get("no_photo_credits", 0)),
                ddg_photo_added=int(tariff.get("ddg_photo_credits", 0)),
                openai_photo_added=int(tariff.get("openai_photo_credits", 0)),
                promo_code=active_promo["code"] if active_promo else None,
            )
            if pend_id > 0:
                await ver_msg.edit_text(
                    f"{ver_res.reason}\n\n"
                    f"⏳ <b>Чек (#{pend_id}) әкімшіге қолмен тексеруге жіберілді!</b>\n"
                    f"Әкімші растаған сәтте сізге хабарлама келеді."
                )
                adm_kb = dict_to_inline_markup(
                    build_admin_payment_review_keyboard(pend_id, int(tariff["credits"]), int(tariff["price_kzt"]))
                )
                for admin_id in config.ADMIN_IDS:
                    try:
                        doc_file = BufferedInputFile(file_bytes, filename=filename)
                        await bot.send_document(
                            chat_id=admin_id,
                            document=doc_file,
                            caption=(
                                f"🎁 <b>ҚОЛМЕН РАСТАУДЫ КҮТЕТІН ЧЕК (#{pend_id})</b>\n"
                                f"👤 Қолданушы: {u_tag} (<code>{uid}</code>)\n"
                                f"📦 Тариф: <b>{tariff['title']}</b> ({tariff['price_kzt']:,} ₸ • +{tariff['credits']} през)\n\n"
                                f"Төмендегі батырмамен қолмен растаңыз немесе қабылдамаңыз:"
                            ),
                            reply_markup=adm_kb,
                        )
                    except Exception:
                        pass
                return
        await ver_msg.edit_text(ver_res.reason)
        return

    payment_id = create_payment_record(
        user_id=uid,
        tariff_id=tariff_id,
        amount_kzt=ver_res.amount_kzt,
        credits_added=ver_res.credits_to_add,
        receipt_hash=ver_res.receipt_hash,
        receipt_number=ver_res.receipt_number,
        status="pending",
        no_photo_added=ver_res.no_photo_to_add,
        ddg_photo_added=ver_res.ddg_photo_to_add,
        openai_photo_added=ver_res.openai_photo_to_add,
        promo_code=active_promo["code"] if active_promo else None,
    )

    if payment_id == 0:
        await ver_msg.edit_text("❌ <b>Бұл чек бұрын пайдаланылған.</b>")
        return

    session.pendingTariffId = None
    if ver_res.openai_photo_to_add > 0:
        session.withPhotos = True
        session.imageSource = "gpt-image-2"
    elif ver_res.ddg_photo_to_add > 0:
        session.withPhotos = True
        session.imageSource = "ddg"
    save_session(message.chat.id, session)

    app_res = approve_payment(payment_id)
    if app_res:
        b = app_res["breakdown"]
        await ver_msg.edit_text(
            f"{ver_res.reason}\n\n"
            f"🎉 <b>Төлем автоматты түрде қабылданды!</b>\n"
            f"📦 Пакет: <b>{tariff['title']}</b>\n"
            f"➕ Қосылды: <b>+{ver_res.credits_to_add} презентация</b> "
            f"({ver_res.no_photo_to_add} фотосыз / {ver_res.ddg_photo_to_add} фотомен / {ver_res.openai_photo_to_add} OpenAI)\n"
            f"🎫 <b>Жалпы балансыңыз: {b['total']} през</b> "
            f"(Бонус: {b['bonus']} | Фотосыз: {b['no_photo']} | Фото: {b['ddg_photo']} | OpenAI: {b['openai_photo']})\n\n"
            f"Енді презентация тақырыбын жаза беріңіз немесе құжат жіберіңіз!"
        )

        if app_res.get("partner_reward_kzt", 0) > 0 and app_res.get("referrer_id"):
            try:
                await bot.send_message(
                    chat_id=app_res["referrer_id"],
                    text=(
                        f"💸 <b>СЕРІКТЕСТІК БОНУС ЕСЕПТЕЛДІ!</b>\n\n"
                        f"Сіз шақырған достардың саудасы <b>{app_res['referrer_sales_total']:,} ₸</b>-ге жетті!\n"
                        f"💰 Балансыңызға <b>+{app_res['partner_reward_kzt']:,} ₸</b> таза табыс қосылды!"
                    ),
                )
            except Exception:
                pass

        for admin_id in config.ADMIN_IDS:
            if admin_id == uid:
                continue
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"✅ <b>ЖАҢА АВТО-ТӨЛЕМ ({ver_res.amount_kzt:,} ₸)</b>\n"
                        f"👤 Қолданушы: {u_tag} (<code>{uid}</code>)\n"
                        f"📦 Пакет: {tariff['title']} (+{ver_res.credits_to_add} през)\n"
                        f"🧾 Чек №: <code>{ver_res.receipt_number or 'PDF'}</code>"
                    ),
                )
            except Exception:
                pass


# ----------------- Document Upload Handler -----------------

@router.message(F.document)
async def handle_document_upload(message: Message, bot: Bot):
    uid = message.from_user.id if message.from_user else message.chat.id
    if message.from_user:
        log_user(uid, message.from_user.username, message.from_user.first_name)

    doc = message.document
    filename = doc.file_name or "document.pdf"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    session = get_telegram_session(message.chat.id)

    file_io = io.BytesIO()
    await bot.download(doc, destination=file_io)
    file_bytes = file_io.getvalue()

    lower_fname = filename.lower()
    is_receipt_filename = any(w in lower_fname for w in ("kaspi", "чек", "квитанц", "түбіртек", "receipt", "check"))
    if ext == ".pdf":
        if not get_seller_setting() and is_admin(uid):
            qr_u, _ = find_qr_url(file_bytes)
            if qr_u or is_receipt_filename:
                await process_kaspi_receipt_upload(message, bot, file_bytes, filename, session)
                return

        if session.pendingTariffId or is_receipt_filename:
            await process_kaspi_receipt_upload(message, bot, file_bytes, filename, session)
            return

        if len(file_bytes) < 600_000:
            raw_latin = file_bytes.decode("latin1", errors="ignore")
            _, text_peek = extract_text_from_uploaded_file(filename, file_bytes)
            qr_u, _ = find_qr_url(file_bytes)
            if (
                qr_u
                or "receipt.kaspi.kz" in raw_latin
                or any(
                    w in text_peek.lower()
                    for w in ("kaspi bank", "kaspi.kz", "төлем сәтті", "платеж успешно", "фискалдық чек", "фискальный чек")
                )
            ):
                await process_kaspi_receipt_upload(message, bot, file_bytes, filename, session)
                return

    if ext not in (".pdf", ".docx", ".pptx", ".txt", ".md"):
        await message.answer(
            "⚠️ Кешіріңіз, тек <b>.PDF, .DOCX, .PPTX</b> немесе <b>.TXT</b> форматындағы құжаттарды жіберуге болады."
        )
        return

    status_msg = await message.answer(f"📥 <b>«{filename}»</b> құжаты оқылуда, күте тұрыңыз...")

    try:
        doc_title, extracted_text = extract_text_from_uploaded_file(filename, file_bytes)
        if not extracted_text or len(extracted_text.strip()) < 20:
            await status_msg.edit_text(
                "⚠️ Құжаттың ішінен мәтін табылмады (немесе ол тек сурет/сканнан тұрады). "
                "Мәтіні бар .DOCX, .PDF немесе .TXT файлын жіберіп көріңіз."
            )
            return

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
        save_session(message.chat.id, session)
        track_funnel_event(uid, "topic_entered", {"source": "document", "topic": doc_title})

        if inline_count:
            await execute_generation(
                bot,
                message.chat.id,
                session,
                user_id=uid,
                slide_count=inline_count,
                existing_msg_id=status_msg.message_id,
            )
            return

        word_count = len(extracted_text.split())
        ready_text = (
            f"✅ <b>Құжат сәтті оқылды!</b> ({word_count} сөз)\n\n"
            + build_topic_ready_text(session, user_id=uid)
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
    uid = message.from_user.id if message.from_user else message.chat.id
    if message.from_user:
        log_user(uid, message.from_user.username, message.from_user.first_name)

    text = message.text.strip()
    chat_id = message.chat.id
    session = get_telegram_session(chat_id)

    only_slide_match = re.match(
        r"^(\d{1,2})\s*(бет|слайд|беттік|слайдтан|страниц|slides)(\s+болсын|\s+жаса|\s+қыл)?$", text, re.IGNORECASE
    )
    if only_slide_match:
        num = max(config.MIN_SLIDE_COUNT, min(int(only_slide_match.group(1)), config.MAX_SLIDE_COUNT))
        session.slideCount = num
        save_session(chat_id, session)
        if session.pendingTopic or session.lastPresentation:
            await execute_generation(bot, chat_id, session, user_id=uid)
        else:
            await message.answer(
                f"✅ Бет саны {num} слайд болып белгіленді. Енді презентация тақырыбын жазыңыз!",
                reply_markup=dict_to_reply_markup(get_persistent_reply_keyboard()),
            )
        return

    clean_topic, inline_count, theme_mention = parse_user_input(text)
    if inline_count:
        session.slideCount = inline_count
    if theme_mention:
        session.designId = theme_mention

    session.pendingTopic = clean_topic
    session.pendingDocumentText = None
    save_session(chat_id, session)
    track_funnel_event(uid, "topic_entered", {"source": "text", "topic": clean_topic})

    if inline_count:
        await execute_generation(bot, chat_id, session, user_id=uid)
        return

    card_text = build_topic_ready_text(session, user_id=uid)
    card_kb = build_topic_ready_keyboard(session)
    await message.answer(card_text, reply_markup=dict_to_inline_markup(card_kb))


# ----------------- Callback Handlers -----------------

@router.callback_query()
async def handle_callback(callback: CallbackQuery, bot: Bot, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()

    global BOT_USERNAME_CACHE
    data = callback.data or ""
    chat_id = callback.message.chat.id
    msg_id = callback.message.message_id
    user_id = callback.from_user.id if callback.from_user else chat_id
    is_doc = bool(getattr(callback.message, "document", None))
    session = get_telegram_session(chat_id)

    if data == "noop":
        await callback.answer()
        return

    # Toggle Photo Mode (none / ddg / gpt-image-2)
    if data.startswith("set_photo:"):
        mode_val = data.split(":")[1]
        enabled_modes = get_enabled_generation_modes()
        if not enabled_modes.get(mode_val, True):
            ensure_session_valid_mode(session)
            save_session(chat_id, session)
            await callback.answer("⚠️ Бұл презентация түрі әкімші тарапынан уақытша өшірілген!", show_alert=True)
            text = build_topic_ready_text(session, user_id=user_id)
            kb = build_topic_ready_keyboard(session)
            try:
                await bot.edit_message_text(
                    text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
                )
            except Exception:
                pass
            return
        if mode_val == "none":
            session.withPhotos = False
            await callback.answer("🚫 Фотосыз режим таңдалды")
        elif mode_val == "ddg":
            session.withPhotos = True
            session.imageSource = "ddg"
            await callback.answer(
                "⚠️ Ескерту: Интернеттен мысал фото алынады (ЖИ қателесуі мүмкін, PPTX-те өзіңіз ауыстыра аласыз)!",
                show_alert=True,
            )
        else:
            session.withPhotos = True
            session.imageSource = "gpt-image-2"
            await callback.answer("✨ OpenAI gpt-image-2 фото режимі таңдалды (VIP/Pro/Хит/500₸)")
        save_session(chat_id, session)
        text = build_topic_ready_text(session, user_id=user_id)
        kb = build_topic_ready_keyboard(session)
        try:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
            )
        except Exception:
            pass
        return

    # Switch Language
    if data.startswith("set_lang:"):
        lang_val = data.split(":")[1]
        if lang_val in config.SUPPORTED_LANGUAGES:
            session.language = lang_val
            save_session(chat_id, session)
            await callback.answer(f"🌐 Тіл: {config.SUPPORTED_LANGUAGES[lang_val]['label']}")
            text = build_topic_ready_text(session, user_id=user_id)
            kb = build_topic_ready_keyboard(session)
            try:
                await bot.edit_message_text(
                    text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
                )
            except Exception:
                pass
        return

    # Open Template Library
    if data.startswith("open_templates"):
        parts = data.split(":")
        mode = parts[1] if len(parts) > 1 else "default"
        await callback.answer()
        tmpl = config.TEMPLATE_LIBRARY.get(session.templateId, config.TEMPLATE_LIBRARY["standard"])
        text = (
            f"📐 <b>ҮЛГІ (TEMPLATE) КІТАПХАНАСЫ</b>\n"
            f"Қазіргі құрылым: <b>{tmpl['title']}</b>\n\n"
            f"Қажетті презентация құрылымын таңдаңыз:"
        )
        kb = build_templates_keyboard(session, mode=mode)
        if not is_doc:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
            )
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        return

    # Pick Template
    if data.startswith("pick_template:"):
        parts = data.split(":")
        t_id = parts[1]
        mode = parts[2] if len(parts) > 2 else "default"
        if t_id in config.TEMPLATE_LIBRARY:
            session.templateId = t_id
            save_session(chat_id, session)
            t_title = config.TEMPLATE_LIBRARY[t_id]["title"]
            await callback.answer(f"✅ Үлгі таңдалды: {t_title}")
            if mode == "topic" and session.pendingTopic:
                text = build_topic_ready_text(session, user_id=user_id)
                kb = build_topic_ready_keyboard(session)
                await bot.edit_message_text(
                    text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
                )
            else:
                await bot.edit_message_text(
                    text=f"✅ Әдепкі құрылым үлгісі сақталды: <b>{t_title}</b>\n\nЕнді презентация тақырыбын жазыңыз!",
                    chat_id=chat_id,
                    message_id=msg_id,
                )
        return

    # 1-Tap Generate Without Photos or With DDG Photos fallback
    if data.startswith("gen_nophoto_now:"):
        n = int(data.split(":")[1])
        session.withPhotos = False
        session.slideCount = n
        save_session(chat_id, session)
        await callback.answer("🚀 Фотосыз презентация дайындалуда...")
        await execute_generation(
            bot, chat_id, session, user_id=user_id, slide_count=n, existing_msg_id=msg_id if not is_doc else None
        )
        return

    if data.startswith("gen_ddg_now:"):
        n = int(data.split(":")[1])
        session.withPhotos = True
        session.imageSource = "ddg"
        session.slideCount = n
        save_session(chat_id, session)
        await callback.answer("🖼 Фотомен (Интернет/ЖИ) презентация дайындалуда...")
        await execute_generation(
            bot, chat_id, session, user_id=user_id, slide_count=n, existing_msg_id=msg_id if not is_doc else None
        )
        return

    # ----------------- ADMIN CONTROL CENTER CALLBACKS -----------------

    # Admin Refresh Dashboard
    if data == "admin_refresh":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return

        text, pend_w, pend_p = format_admin_dashboard_text()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(build_admin_keyboard(pend_w, pend_p)))
            await callback.answer("Жаңартылды!")
        except Exception:
            await callback.message.answer(text, reply_markup=dict_to_inline_markup(build_admin_keyboard(pend_w, pend_p)))
            await callback.answer()
        return

    # Admin 7-Day / 30-Day Charts (PNG)
    if data.startswith("admin_charts:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        days = int(data.split(":")[1])
        await callback.answer(f"📊 {days} күндік график сызылуда...")
        png_bytes, cap = render_admin_analytics_chart_png(days=days)
        photo_file = BufferedInputFile(png_bytes, filename=f"analytics_{days}d.png")
        await bot.send_photo(
            chat_id=chat_id,
            photo=photo_file,
            caption=cap,
            reply_markup=dict_to_inline_markup({
                "inline_keyboard": [
                    [
                        {"text": "📊 7 күндік", "callback_data": "admin_charts:7"},
                        {"text": "📈 30 күндік", "callback_data": "admin_charts:30"},
                    ],
                    [{"text": "⬅️ Админ панельге оралу", "callback_data": "admin_refresh"}],
                ]
            }),
        )
        return

    # Admin Paginated & Filtered Users List
    if data.startswith("admin_users:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        parts = data.split(":")
        page = int(parts[1]) if len(parts) > 1 else 0
        f_mode = parts[2] if len(parts) > 2 else "all"
        users, total = get_users_paginated(page=page, page_size=8, filter_mode=f_mode)
        filter_titles = {
            "all": "Барлық қолданушылар",
            "photo": "Тек фотомен презентация жасағандар",
            "paid": "Тек төлем жасағандар (VIP/Pro/Хит)",
            "active": "Соңғы 7 күнде белсенділер",
        }
        text = (
            f"👥 <b>ҚОЛДАНУШЫЛАР ТІЗІМІ ({total} адам)</b>\n"
            f"🔍 Фильтр: <b>{filter_titles.get(f_mode, f_mode)}</b>\n\n"
            f"Кез келген қолданушыны басып, оның толық 360° тарихын көре аласыз:"
        )
        kb = build_admin_users_list_keyboard(users, page=page, total_count=total, filter_mode=f_mode)
        await callback.answer()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(kb))
        except Exception:
            await callback.message.answer(text, reply_markup=dict_to_inline_markup(kb))
        return

    # Admin Promo Codes & Bonus Campaigns Management
    if data == "admin_promos":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        promos = list_all_promo_codes()
        lines = [
            "🎟 <b>ПРОМОКОДТАР ЖӘНЕ СЫЙЛЫҚ НАУҚАНДАРЫ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📌 Ереже: Әр промокод бір қолданушыға <b>тек 1 рет қана</b> істейді!\n"
        ]
        for pr in promos:
            disc = int(pr.get("discount_percent") or 0)
            bon = int(pr.get("bonus_credits") or 0)
            eff = f"+{bon} тегін през" if bon > 0 and disc == 0 else f"-{disc}% жеңілдік"
            lines.append(f"• <code>{pr['code']}</code> — <b>{eff}</b> (Қолданылды: {pr['used_count']} рет)")
        await callback.answer()
        kb = build_admin_promos_keyboard(promos)
        try:
            await callback.message.edit_text("\n".join(lines), reply_markup=dict_to_inline_markup(kb))
        except Exception:
            await callback.message.answer("\n".join(lines), reply_markup=dict_to_inline_markup(kb))
        return

    if data.startswith("adm_del_promo:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        code = data.split(":")[1]
        delete_promo_code(code)
        await callback.answer(f"🗑 {code} өшірілді!")
        promos = list_all_promo_codes()
        try:
            await callback.message.edit_reply_markup(reply_markup=dict_to_inline_markup(build_admin_promos_keyboard(promos)))
        except Exception:
            pass
        return

    # Admin Toggle / Delete / Re-enable Tariff Package
    if data.startswith("adm_toggle_pkg:") or data.startswith("adm_del_pkg:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        pkg_id = data.split(":")[1]
        now_enabled = toggle_tariff_package(pkg_id)
        await callback.answer("🟢 Пакет қайта қосылды!" if now_enabled else "🔴 Пакет уақытша өшірілді!")
        text, kb = get_admin_price_editor_message()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(kb))
        except Exception:
            pass
        return

    if data == "adm_enable_all_pkgs":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        enable_all_tariff_packages()
        await callback.answer("🟢 Барлық тарифтік пакеттер қосылды!")
        text, kb = get_admin_price_editor_message()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(kb))
        except Exception:
            pass
        return

    # Admin 3 Presentation Generation Modes Control (Фотосыз / Фото / OpenAI)
    if data == "admin_gen_modes":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        await callback.answer()
        text, kb = get_admin_gen_modes_message()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(kb))
        except Exception:
            await callback.message.answer(text, reply_markup=dict_to_inline_markup(kb))
        return

    if data.startswith("adm_toggle_mode:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        mode_key = data.split(":")[1]
        ok, modes = toggle_generation_mode(mode_key)
        if not ok:
            await callback.answer("⚠️ Кемінде 1 презентация түрі қосулы қалуы керек!", show_alert=True)
            return
        st_txt = "🟢 Қосылды!" if modes.get(mode_key) else "🔴 Өшірілді!"
        await callback.answer(st_txt)
        text, kb = get_admin_gen_modes_message()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(kb))
        except Exception:
            pass
        return

    if data.startswith("adm_mode_preset:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        preset = data.split(":")[1]
        if preset == "only_nophoto":
            set_only_nophoto_mode()
            await callback.answer("📄 Тек «Фотосыз» режимі қалдырылды!")
        else:
            enable_all_generation_modes()
            await callback.answer("🔄 Барлық 3 презентация түрі қосылды!")
        text, kb = get_admin_gen_modes_message()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(kb))
        except Exception:
            pass
        return

    # Admin AI Cost Tracker Screen
    if data == "admin_ai_costs":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        st = get_ai_cost_stats()
        lines = [
            "📈 <b>AI ШЫҒЫНДАРЫН БАҚЫЛАУ (ОПТИМИЗАЦИЯ)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <b>Қосылған үнемдеу ережелері:</b>\n"
            "• Негізгі AI: <b>DeepSeek</b> (~$0.0015 / през)\n"
            "• Тегін қолданушылар: тек <b>DeepSeek → Fallback</b> (OpenAI/Gemini шақырылмайды!)\n"
            "• <code>gpt-image-2</code> (~$0.02/сурет): тек <b>VIP / Pro / Хит / 500₸</b> пакеттеріне ғана рұқсат етілген!\n\n"
            f"💰 <b>Бүгінгі шығын:</b> <b>${st['today_usd']:.4f} (~{st['today_kzt']} ₸)</b> ({st['today_calls']} сұраныс)\n"
            f"🏦 <b>Жалпы шығын:</b> <b>${st['total_usd']:.4f} (~{st['total_kzt']} ₸)</b> ({st['total_calls']} сұраныс)\n\n"
            "📊 <b>Модельдер бойынша бөлініс:</b>"
        ]
        for r in st["by_provider"]:
            lines.append(
                f"  • <code>{r['provider']}</code>: <b>{r['calls']} рет</b> — ${float(r['usd']):.4f} (~{int(r['kzt'])} ₸)"
            )
        if not st["by_provider"]:
            lines.append("  (Әзірге шығын жазбалары жоқ)")
        await callback.answer()
        kb = {"inline_keyboard": [[{"text": "⬅️ Админ панельге оралу", "callback_data": "admin_refresh"}]]}
        try:
            await callback.message.edit_text("\n".join(lines), reply_markup=dict_to_inline_markup(kb))
        except Exception:
            await callback.message.answer("\n".join(lines), reply_markup=dict_to_inline_markup(kb))
        return

    # Admin Segmented Broadcast Menu
    if data == "admin_broadcast_menu":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        await callback.answer()
        text = (
            "📢 <b>СЕГМЕНТТІК ХАБАРЛАМА ТАРАТУ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Хабарламаны қай аудиторияға жібергіңіз келеді?"
        )
        kb = build_admin_broadcast_segment_keyboard()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(kb))
        except Exception:
            await callback.message.answer(text, reply_markup=dict_to_inline_markup(kb))
        return

    # Admin Export Database (CSV / Excel ZIP)
    if data == "admin_export_db":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        await callback.answer("💾 Дерекқор CSV/Excel форматында дайындалуда...")
        zip_bytes, fname = export_database_zip_bytes()
        doc_file = BufferedInputFile(zip_bytes, filename=fname)
        await bot.send_document(
            chat_id=chat_id,
            document=doc_file,
            caption=(
                "💾 <b>Дерекқор экспорты дайын (Excel UTF-8 CSV)!</b>\n"
                "Архив ішінде: <code>users.csv</code>, <code>payments.csv</code>, <code>generations.csv</code>, <code>ai_costs.csv</code>, <code>promo_codes.csv</code>"
            ),
        )
        return

    # Admin Delete User Project from 360° Card
    if data.startswith("adm_del_proj:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        parts = data.split(":")
        proj_id = int(parts[1])
        target_uid = int(parts[2])
        deleted = delete_user_project_by_id(proj_id)
        await callback.answer("🗑 Жоба өшірілді!" if deleted else "Жоба табылмады")
        card_text, projects = format_user_admin_card(target_uid)
        kb = dict_to_inline_markup(build_admin_user_manage_keyboard(target_uid, projects=projects))
        try:
            await callback.message.edit_text(card_text, reply_markup=kb)
        except Exception:
            pass
        return

    # Admin Manual Approve / Reject Payment Receipt
    if data.startswith("approve_pay:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        pay_id = int(data.split(":")[1])
        app_res = approve_payment(pay_id)
        if not app_res:
            await callback.answer("Бұл төлем бұрын өңделген.", show_alert=True)
            return
        await callback.answer("✅ Төлем қолмен расталды!")
        try:
            await callback.message.edit_caption(
                caption=(callback.message.caption or "") + f"\n\n✅ <b>РАСТАЛДЫ (+{app_res['credits_added']} през)</b>"
            )
        except Exception:
            try:
                await callback.message.edit_text(
                    (callback.message.text or "") + f"\n\n✅ <b>РАСТАЛДЫ (+{app_res['credits_added']} през)</b>"
                )
            except Exception:
                pass
        try:
            await bot.send_message(
                chat_id=app_res["user_id"],
                text=(
                    f"🎉 <b>Сіздің чегіңіз (#{pay_id}) әкімші тарапынан расталды!</b>\n"
                    f"➕ Қосылды: <b>+{app_res['credits_added']} презентация</b>\n"
                    f"🎫 Жалпы балансыңыз: <b>{app_res['new_credits']} презентация</b>"
                ),
            )
        except Exception:
            pass
        return

    if data.startswith("reject_pay:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        pay_id = int(data.split(":")[1])
        rej = reject_payment(pay_id)
        if not rej:
            await callback.answer("Бұл төлем бұрын өңделген.", show_alert=True)
            return
        await callback.answer("❌ Төлем қабылданбады")
        try:
            await callback.message.edit_caption(caption=(callback.message.caption or "") + "\n\n❌ <b>ҚАБЫЛДАНБАДЫ</b>")
        except Exception:
            pass
        try:
            await bot.send_message(
                chat_id=rej["user_id"],
                text=f"❌ <b>Сіздің #{pay_id} төлем чегіңіз расталмады.</b> Түпнұсқа Kaspi Pay PDF чегін жіберіңіз немесе админге жазыңыз.",
            )
        except Exception:
            pass
        return

    # Admin Open Kaspi Pay & Seller Settings
    if data == "admin_kaspi_settings":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        await callback.answer()
        text, kb = get_admin_kaspi_settings_message()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(kb))
        except Exception:
            await callback.message.answer(text, reply_markup=dict_to_inline_markup(kb))
        return

    # Admin Reset Seller Company
    if data == "admin_reset_seller":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        reset_seller_setting()
        await callback.answer("✅ Компания тазаланды!")
        text, kb = get_admin_kaspi_settings_message()
        try:
            await callback.message.edit_text(
                "✅ <b>Ескі компания тазаланды!</b>\n"
                "👉 Енді чатқа жаңа Kaspi Pay-дің <b>бірінші PDF чегін</b> жіберіңіз — бот оны автоматты түрде есте сақтайды.\n\n"
                + text,
                reply_markup=dict_to_inline_markup(kb),
            )
        except Exception:
            pass
        return

    # Admin Open Dynamic Price Editor
    if data == "admin_edit_prices":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        await callback.answer()
        text, kb = get_admin_price_editor_message()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(kb))
        except Exception:
            await callback.message.answer(text, reply_markup=dict_to_inline_markup(kb))
        return

    # Admin View Pending Withdrawals Queue
    if data == "admin_withdrawals":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return

        await callback.answer()
        pending_list = get_pending_withdrawals()
        if not pending_list:
            await callback.message.answer("✅ Қазіргі сәтте күтілудегі шығару сұраныстары жоқ.")
            return

        for w in pending_list[:10]:
            u_name = f"@{w['username']}" if w.get("username") else (w.get("first_name") or str(w["user_id"]))
            w_text = (
                f"💸 <b>ШЫҒАРУ СҰРАНЫСЫ #{w['id']}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Студент: {u_name} (ID: <code>{w['user_id']}</code>)\n"
                f"💵 <b>Төленетін сома: {w['amount_kzt']:,} ₸</b>\n"
                f"💳 <b>Реквизит:</b> <code>{w['requisites']}</code>"
            )
            kb = dict_to_inline_markup(build_admin_withdrawal_action_keyboard(w["id"], w["amount_kzt"]))
            await callback.message.answer(w_text, reply_markup=kb)
        return

    # Admin Click "✅ Төленді" on Partner Withdrawal
    if data.startswith("pay_withdraw:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return

        w_id = int(data.split(":")[1])
        w_res = approve_withdrawal_request(w_id)
        if not w_res:
            await callback.answer("Бұл сұраныс бұрын өңделген.", show_alert=True)
            return

        await callback.answer("✅ Төленді деп белгіленді!")
        try:
            await callback.message.edit_text(
                (callback.message.text or "")
                + f"\n\n✅ <b>ТӨЛЕНДІ ({w_res['amount_kzt']:,} ₸) — Баланстан шегерілді!</b>"
            )
        except Exception:
            pass

        try:
            await bot.send_message(
                chat_id=w_res["user_id"],
                text=(
                    f"🎉 <b>Сіздің табыс шығару сұранысыңыз төленді!</b>\n"
                    f"💵 Төленген сома: <b>{w_res['amount_kzt']:,} ₸</b>\n"
                    f"💰 Қалған серіктестік балансыңыз: <b>{w_res['new_balance']:,} ₸</b>"
                ),
            )
        except Exception:
            pass
        return

    # Admin Reject Partner Withdrawal
    if data.startswith("reject_withdraw:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return

        w_id = int(data.split(":")[1])
        w_rej = reject_withdrawal_request(w_id)
        if not w_rej:
            await callback.answer("Бұл сұраныс бұрын өңделген.", show_alert=True)
            return

        await callback.answer("❌ Сұраныс қайтарылды")
        try:
            await callback.message.edit_text((callback.message.text or "") + "\n\n❌ <b>БАС ТАРТЫЛДЫ</b>")
        except Exception:
            pass
        return

    # Admin View Recent & Pending Payments (with Manual Approve buttons for pending receipts)
    if data == "admin_payments":
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return

        await callback.answer()
        pays = get_recent_payments(10)
        if not pays:
            await callback.message.answer("🧾 Әзірге төлем чектері тіркелмеген.")
            return

        for p in pays[:8]:
            u_name = f"@{p['username']}" if p.get("username") else (p.get("first_name") or str(p["user_id"]))
            st_icon = "✅" if p["status"] == "approved" else ("⏳ КҮТІЛУДЕ" if p["status"] == "pending" else "❌")
            r_no = p.get("receipt_number") or "PDF"
            p_text = (
                f"{st_icon} <b>Төлем #{p['id']}</b> • {u_name} (<code>{p['user_id']}</code>)\n"
                f"💵 Сома: <b>{p['amount_kzt']:,} ₸</b> (+{p['credits_added']} през) • Чек: <code>{r_no}</code>"
            )
            if p["status"] == "pending":
                kb = dict_to_inline_markup(
                    build_admin_payment_review_keyboard(p["id"], int(p["credits_added"]), int(p["amount_kzt"]))
                )
                await callback.message.answer(p_text, reply_markup=kb)
            else:
                await callback.message.answer(p_text)
        return

    # Admin View Specific User 360° Card
    if data.startswith("adm_view_user:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        target_uid = int(data.split(":")[1])
        card_text, projects = format_user_admin_card(target_uid)
        await callback.answer()
        await callback.message.answer(
            card_text,
            reply_markup=dict_to_inline_markup(build_admin_user_manage_keyboard(target_uid, projects=projects)),
        )
        return

    # Admin 1-Tap Modify User Credits
    if data.startswith("adm_cred:"):
        if not is_admin(user_id):
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        parts = data.split(":")
        target_uid = int(parts[1])
        delta = int(parts[2])
        if delta == 20:
            new_bal = add_user_credits(target_uid, 20, no_photo_to_add=10, ddg_photo_to_add=5, openai_photo_to_add=5)
        elif delta == 30:
            new_bal = add_user_credits(target_uid, 30, no_photo_to_add=10, ddg_photo_to_add=10, openai_photo_to_add=10)
        elif delta == 80:
            new_bal = add_user_credits(target_uid, 80, no_photo_to_add=40, ddg_photo_to_add=20, openai_photo_to_add=20)
        else:
            new_bal = add_user_credits(target_uid, delta, is_bonus=(delta > 0))

        card_text, projects = format_user_admin_card(target_uid)
        await callback.answer(f"Баланс өзгертілді: {new_bal} през!")
        try:
            await callback.message.edit_text(
                card_text,
                reply_markup=dict_to_inline_markup(build_admin_user_manage_keyboard(target_uid, projects=projects)),
            )
        except Exception:
            pass

        if delta > 0:
            try:
                await bot.send_message(
                    chat_id=target_uid,
                    text=(
                        f"🎁 <b>Құттықтаймыз!</b>\n"
                        f"Әкімші сіздің балансыңызға <b>+{delta} презентация</b> қосты!\n"
                        f"🎫 Қазіргі балансыңыз: <b>{new_bal} презентация</b>."
                    ),
                )
            except Exception:
                pass
        return

    # Open Tariffs Menu
    if data == "open_tariffs":
        await callback.answer()
        track_funnel_event(user_id, "tariff_viewed")
        text, kb = get_tariffs_message(user_id)
        if not is_doc:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
            )
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        return

    # Select Tariff to Buy via Kaspi Pay Link
    if data.startswith("buy_tariff:"):
        tariff_id = data.split(":")[1]
        session.pendingTariffId = tariff_id
        save_session(chat_id, session)
        await callback.answer()
        text, kb = get_payment_instruction_message(tariff_id, user_id=user_id)
        if not is_doc:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
            )
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        return

    # Open Referral & Partner Earnings Menu
    if data == "open_referral":
        await callback.answer()
        try:
            me = await bot.get_me()
            if me.username:
                BOT_USERNAME_CACHE = me.username
        except Exception:
            pass
        text, kb = get_referral_message(user_id, BOT_USERNAME_CACHE)
        if not is_doc:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
            )
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        return

    # Paginate Saved Projects
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
            f"Жобаны басып, оны <b>.PPTX + .PDF + .DOCX</b> түрінде қайта жүктеп алуға болады:"
        )
        kb = build_user_projects_keyboard(projects, page=page, total_count=total, page_size=page_size)
        if not is_doc:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
            )
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        return

    # Load Saved Project (sends all 3 files: .PPTX + .PDF + .DOCX)
    if data.startswith("load_proj:"):
        proj_id = int(data.split(":")[1])
        await callback.answer("📂 Жоба жүктелуде (.PPTX + .PDF + .DOCX)...")
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

        loaded = load_saved_project_for_session(session, proj_id, user_id=user_id)
        if not loaded:
            await callback.message.answer("❌ Жоба табылмады.")
            return
        save_session(chat_id, session)

        pptx_bytes, filename, pres, theme_name_kz = loaded
        await send_all_three_presentation_files(
            bot=bot,
            chat_id=chat_id,
            session=session,
            pptx_bytes=pptx_bytes,
            pptx_filename=filename,
            theme_name_kz=theme_name_kz,
            rem_credits=get_user_credits(user_id),
            from_cache=True,
        )
        return

    # 1-Tap Generate
    if data.startswith("gen_now:"):
        n = int(data.split(":")[1])
        session.slideCount = n
        save_session(chat_id, session)
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
        save_session(chat_id, session)
        await callback.answer(f"✅ Әдепкі бет саны: {n} бет")
        if session.pendingTopic:
            text = build_topic_ready_text(session, user_id=user_id)
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

    # 35-Themes Menu
    if data.startswith("open_themes:"):
        parts = data.split(":")
        page = int(parts[1]) if len(parts) > 1 else 0
        mode = parts[2] if len(parts) > 2 else "default"
        session.themePage = page
        save_session(chat_id, session)
        await callback.answer()

        text = (
            "🎨 Жаңа дизайнды бассаңыз, дайын файлдар (.PPTX + .PDF + .DOCX) бірден сол дизайнмен қайта жіберіледі:"
            if mode == "reexport"
            else f"🎨 35 кәсіби дизайн ішінен ұнағанын таңдаңыз\n(Қазіргі: {get_selected_theme_label(session.designId, session.pendingTopic, with_photos=session.withPhotos)}):"
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
        save_session(chat_id, session)
        label = get_selected_theme_label(theme_id, session.pendingTopic, with_photos=session.withPhotos)
        await callback.answer(f"✅ Таңдалды: {label}")

        if session.pendingTopic:
            text = build_topic_ready_text(session, user_id=user_id)
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

    # Instant Re-export (sends .PPTX + .PDF + .DOCX with the new design!)
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
        save_session(chat_id, session)

        pptx_bytes, filename, theme_name_kz = res
        await callback.answer(f"🎨 «{theme_name_kz}» дизайнымен жіберілуде...")
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

        await send_all_three_presentation_files(
            bot=bot,
            chat_id=chat_id,
            session=session,
            pptx_bytes=pptx_bytes,
            pptx_filename=filename,
            theme_name_kz=theme_name_kz,
            rem_credits=get_user_credits(user_id),
            from_cache=True,
        )
        return

    # Back to topic
    if data == "back_to_topic":
        await callback.answer()
        text = build_topic_ready_text(session, user_id=user_id)
        kb = build_topic_ready_keyboard(session)
        if not is_doc:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=msg_id, reply_markup=dict_to_inline_markup(kb)
            )
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=dict_to_inline_markup(kb))
        return


async def main():
    global BOT_USERNAME_CACHE
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment or .env file!")
        return

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    try:
        me = await bot.get_me()
        if me.username:
            BOT_USERNAME_CACHE = me.username
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Ботты іске қосу"),
                BotCommand(command="tariffs", description="💳 Баланс және Тарифтер"),
                BotCommand(command="promo", description="🎟 1-реттік Промокод енгізу"),
                BotCommand(command="templates", description="📐 Үлгілер (Шаблон)"),
                BotCommand(command="projects", description="📂 Менің жобаларым"),
                BotCommand(command="referral", description="👥 Реферал және Табыс табу"),
                BotCommand(command="support", description="👨‍💻 Админмен байланыс"),
                BotCommand(command="admin", description="📊 Әкімші панелі"),
            ]
        )
    except Exception as e:
        logger.warning(f"Could not initialize bot metadata: {e}")

    logger.info(f"🤖 AI Presentation Telegram Bot Pro v2 (@{BOT_USERNAME_CACHE}) started successfully!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
