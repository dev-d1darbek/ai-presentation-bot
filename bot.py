"""
Production AI Presentation Bot using Aiogram 3.
Complete Commercial Edition with test.py Kaspi Fiscal Auto-Setup & Dynamic Price Editor:
1. First Receipt Auto-Setup (Admin sends 1st PDF receipt -> bot memorizes seller company + 12-digit BIN; /reset or Admin button resets it anytime)
2. Kaspi Pay Link Only (No phone transfers; Admin can update Kaspi Pay URL anytime inside /admin)
3. Dynamic Tariff Price Editor in Bot (Admin can freely change tariff prices & slide credits anytime inside /admin)
4. 100% Automatic Fiscal Receipt Verification (receipt.kaspi.kz Nuxt parser + duplicate check + company BIN check + amount match)
5. Welcome Free Credit (1 free presentation), 2-Tier Referral & Partner Program (min 2,000 ₸ custom withdrawal with Admin "Төленді" deduction)
6. Document-to-Slide (.PDF / .DOCX / .PPTX / .TXT), Speaker Defense Speech (.DOCX), Saved Projects, Smart Cross-User Cache, and 2-Way Admin Support
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
from app.core.db import (
    log_user,
    get_user_profile,
    find_user_by_query,
    get_user_credits,
    consume_user_credit,
    add_user_credits,
    get_seller_setting,
    reset_seller_setting,
    get_kaspi_pay_url,
    set_kaspi_pay_url,
    get_dynamic_tariffs,
    update_tariff_setting,
    create_payment_record,
    approve_payment,
    reject_payment,
    create_withdrawal_request,
    approve_withdrawal_request,
    reject_withdrawal_request,
    get_pending_withdrawals,
    get_recent_payments,
    get_all_user_ids,
    get_user_projects,
)
from app.core.verifier import (
    verify_kaspi_receipt,
    save_company_from_first_receipt,
    find_qr_url,
)
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
    build_tariffs_keyboard,
    build_admin_withdrawal_action_keyboard,
    build_admin_keyboard,
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
    format_user_admin_card,
    format_admin_dashboard_text,
)
from app.bot.handlers.commands import (
    get_start_message,
    get_tariffs_message,
    get_payment_instruction_message,
    get_admin_kaspi_settings_message,
    get_admin_price_editor_message,
    get_referral_message,
    get_support_message,
    get_help_message,
    get_slides_message,
    get_design_message,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = Router()
BOT_USERNAME_CACHE: str = "ai_presentation_bot"


class BotStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_withdrawal_amount = State()
    waiting_for_withdrawal_requisites = State()
    waiting_for_support_message = State()
    waiting_for_admin_reply = State()
    waiting_for_admin_user_search = State()
    waiting_for_kaspi_pay_url = State()
    waiting_for_tariff_price = State()


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
                    f"🎁 Сізге <b>+1 ТЕГІН презентация</b> берілді!"
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


async def execute_generation(
    bot: Bot,
    chat_id: int,
    session,
    user_id: Optional[int] = None,
    slide_count: Optional[int] = None,
    existing_msg_id: Optional[int] = None,
):
    uid = user_id or chat_id
    is_admin = uid in config.ADMIN_IDS
    credits = get_user_credits(uid)

    if credits <= 0 and not is_admin:
        t_text, t_kb = get_tariffs_message(uid)
        out_of_credits_msg = (
            "⚠️ <b>Сіздің тегін презентация лимитіңіз аяқталды (Баланс: 0).</b>\n\n"
            "Жаңа презентация жасау үшін төмендегі тиімді пакеттердің бірін таңдаңыз "
            "немесе <b>2 досыңызды шақырып +1 тегін презентация</b> алыңыз!\n\n"
            + t_text
        )
        if existing_msg_id:
            try:
                await bot.edit_message_text(
                    text=out_of_credits_msg,
                    chat_id=chat_id,
                    message_id=existing_msg_id,
                    reply_markup=dict_to_inline_markup(t_kb),
                )
                return
            except Exception:
                pass
        await bot.send_message(chat_id=chat_id, text=out_of_credits_msg, reply_markup=dict_to_inline_markup(t_kb))
        return

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
            session, user_id=uid, slide_count=count
        )
        if not is_admin:
            consume_user_credit(uid)
        rem_credits = get_user_credits(uid)

        speed_badge = "⚡ <i>Жылдам кэштен лезде дайындалды</i>\n" if from_cache else ""
        caption = (
            f"✅ <b>Презентация дайын!</b>\n"
            f"{speed_badge}"
            f"📌 Тақырып: {topic}\n"
            f"📄 Бет саны: {presentation.slide_count} слайд\n"
            f"🎨 Дизайн: {selected_theme.nameKz}\n"
            f"🎫 Қалған лимит: {rem_credits} презентация\n\n"
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


# ----------------- Command & Main Menu Handlers -----------------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    referrer_id = None
    parts = (message.text or "").split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        ref_str = parts[1].replace("ref_", "").strip()
        if ref_str.isdigit():
            referrer_id = int(ref_str)

    reg_res = {"is_new": False}
    if message.from_user:
        reg_res = log_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            referrer_id=referrer_id,
        )
        await notify_referrer_bonuses(bot, reg_res)

    text, kb = get_start_message(message.chat.id, is_new=reg_res.get("is_new", False))
    await message.answer(text, reply_markup=dict_to_reply_markup(kb))


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Shows saved Kaspi Pay company & BIN status (matching test.py /status)."""
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
    """Clears saved company so the next PDF receipt sets the new company (matching test.py /reset)."""
    uid = message.from_user.id if message.from_user else 0
    if config.ADMIN_IDS and uid not in config.ADMIN_IDS:
        await message.answer("❌ Тек админ үшін.")
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
        f"Кез келген жобаны басып, оны <b>.PPTX</b>, <b>.PDF</b>, <b>🎤 Қорғау сөзі</b> ретінде жүктеп алуға "
        f"немесе дизайнын 1 секундта ауыстыруға болады:"
    )
    kb = build_user_projects_keyboard(projects, page=0, total_count=total)
    await message.answer(text, reply_markup=dict_to_inline_markup(kb))


# ----------------- Admin Commands (/admin and /give) -----------------

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id if message.from_user else 0
    if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
        await message.answer("⛔️ Бұл команда тек бот әкімшісіне арналған.")
        return

    text, pend_w = format_admin_dashboard_text()
    if not config.ADMIN_IDS:
        text += f"\n\n💡 <i>Кеңес: Қауіпсіздік үшін өз Telegram ID-іңізді (<code>{user_id}</code>) .env файлына ADMIN_IDS={user_id} деп жазып қойыңыз.</i>"

    await message.answer(text, reply_markup=dict_to_inline_markup(build_admin_keyboard(pend_w)))


@router.message(Command("give"))
async def cmd_give(message: Message, bot: Bot):
    admin_id = message.from_user.id if message.from_user else 0
    if config.ADMIN_IDS and admin_id not in config.ADMIN_IDS:
        await message.answer("⛔️ Бұл команда тек бот әкімшісіне арналған.")
        return

    parts = (message.text or "").split()
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer(
            "ℹ️ <b>Қолдану үлгісі:</b>\n"
            "<code>/give USER_ID САНЫ</code>\n\n"
            "Мысалы:\n"
            "• <code>/give 1234567 5</code> — 5 презентация қосу\n"
            "• <code>/give 1234567 hit</code> — Хит пакетін қосу\n"
            "• <code>/give 1234567 vip</code> — VIP пакетін қосу"
        )
        return

    target_uid = int(parts[1])
    raw_val = parts[2].lower().strip()
    tariffs = get_dynamic_tariffs()
    if raw_val == "vip":
        credits_to_give = tariffs["vip"]["credits"]
    elif raw_val == "hit":
        credits_to_give = tariffs["hit"]["credits"]
    elif raw_val.lstrip("-").isdigit():
        credits_to_give = int(raw_val)
    else:
        await message.answer("⚠️ Қате мән. Сан жазыңыз немесе <code>vip</code> / <code>hit</code> деп көрсетіңіз.")
        return

    new_bal = add_user_credits(target_uid, credits_to_give)
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


# ----------------- FSM States: Kaspi Pay Link, Dynamic Prices, Withdrawals, Support -----------------

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Әрекет тоқтатылды.", reply_markup=dict_to_reply_markup(get_persistent_reply_keyboard()))


# 1. Admin Change Kaspi Pay URL
@router.callback_query(F.data == "admin_set_pay_url")
async def cb_admin_set_pay_url(callback: CallbackQuery, state: FSMContext):
    if config.ADMIN_IDS and callback.from_user.id not in config.ADMIN_IDS:
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


# 2. Admin Edit Tariff Prices Dynamically
@router.callback_query(F.data.startswith("edit_tariff:"))
async def cb_edit_tariff(callback: CallbackQuery, state: FSMContext):
    if config.ADMIN_IDS and callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return

    tariff_id = callback.data.split(":")[1]
    tariffs = get_dynamic_tariffs()
    t = tariffs.get(tariff_id, tariffs["hit"])

    await state.update_data(edit_tariff_id=tariff_id)
    await state.set_state(BotStates.waiting_for_tariff_price)
    await callback.message.answer(
        f"✏️ <b>{t['title']} тарифін өзгерту</b>\n"
        f"Қазіргі бағасы: <b>{t['price_kzt']:,} ₸</b> ({t['credits']} презентация)\n\n"
        f"💵 <b>Жаңа бағаны (теңгемен) жазыңыз:</b>\n"
        f"• Тек бағаны өзгерту үшін: мысалы <code>{t['price_kzt']}</code>\n"
        f"• Баға мен презентация санын бірге өзгерту үшін бос орын арқылы: мысалы <code>2500 20</code> (2500 ₸ және 20 презентация)\n\n"
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
    new_credits = nums[1] if len(nums) > 1 and nums[1] > 0 else None

    updated = update_tariff_setting(tariff_id, price_kzt=new_price, credits=new_credits)
    text, kb = get_admin_price_editor_message()
    await message.answer(
        f"✅ <b>{updated['title']} жаңартылды: {updated['price_kzt']:,} ₸ ({updated['credits']} презентация)!</b>\n\n{text}",
        reply_markup=dict_to_inline_markup(kb),
    )


# 3. Partner Withdrawal Flow (Step 1: Amount -> Step 2: Kaspi phone or card number)
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
                    f"👥 Шақырған достары: <b>{profile.get('invited_count', 0)} адам</b>\n"
                    f"🛍 Реферал саудасы: <b>{profile.get('referral_sales_kzt', 0):,} ₸</b>\n"
                    f"💰 Қазіргі балансы: <b>{profile.get('partner_balance_kzt', 0):,} ₸</b>\n\n"
                    f"💵 <b>Сұраған сомасы: {amount:,} ₸</b>\n"
                    f"💳 <b>Kaspi / Карта:</b> <code>{requisites}</code>\n\n"
                    f"Аударым жасаған соң төмендегі «✅ Төленді» батырмасын басыңыз:"
                ),
                reply_markup=adm_kb,
            )
        except Exception:
            pass


# 4. User Support Message & Admin Reply
@router.callback_query(F.data == "start_support_msg")
async def cb_start_support_msg(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_support_message)
    await callback.message.answer(
        "✍️ <b>Әкімшіге жазатын сұрағыңызды немесе хабарламаңызды осында жазып жіберіңіз</b> "
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
                    f"📩 <b>ҚОЛДАНУШЫДАН ХАБАРЛАМА</b>\n"
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
    if config.ADMIN_IDS and callback.from_user.id not in config.ADMIN_IDS:
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


# 5. Admin User Search & Management
@router.callback_query(F.data == "admin_find_user")
async def cb_admin_find_user(callback: CallbackQuery, state: FSMContext):
    if config.ADMIN_IDS and callback.from_user.id not in config.ADMIN_IDS:
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

    card_text = format_user_admin_card(prof)
    kb = dict_to_inline_markup(build_admin_user_manage_keyboard(prof["user_id"]))
    await message.answer(card_text, reply_markup=kb)


# 6. Admin Broadcast
@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
        await callback.answer("Рұқсат жоқ", show_alert=True)
        return

    await state.set_state(BotStates.waiting_for_broadcast)
    await callback.message.answer(
        "📢 Барлық пайдаланушыларға тарататын хабарлама мәтінін жазыңыз (немесе бас тарту үшін /cancel):"
    )
    await callback.answer()


@router.message(BotStates.waiting_for_broadcast)
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


# ----------------- Kaspi Pay Receipt Auto-Setup & Auto-Verification -----------------

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

    # 1. Exact test.py logic: If 'seller' is not set yet, the first PDF receipt memorizes the seller company + BIN!
    seller = get_seller_setting()
    if not seller:
        ok, setup_msg, _ = save_company_from_first_receipt(uid, file_bytes)
        await ver_msg.edit_text(setup_msg)
        return

    # 2. Verify subsequent receipts against saved company, Kaspi server, duplicate check, and dynamic tariff prices
    ver_res = verify_kaspi_receipt(
        file_bytes=file_bytes,
        filename=filename,
        expected_tariff_id=session.pendingTariffId,
        user_id=uid,
    )

    if ver_res.is_duplicate or not ver_res.is_valid:
        await ver_msg.edit_text(ver_res.reason)
        return

    tariffs = get_dynamic_tariffs()
    tariff_id = ver_res.matched_tariff_id or session.pendingTariffId or "hit"
    tariff = tariffs.get(tariff_id, tariffs["hit"])

    payment_id = create_payment_record(
        user_id=uid,
        tariff_id=tariff_id,
        amount_kzt=ver_res.amount_kzt,
        credits_added=ver_res.credits_to_add,
        receipt_hash=ver_res.receipt_hash,
        receipt_number=ver_res.receipt_number,
        status="pending",
    )

    session.pendingTariffId = None

    app_res = approve_payment(payment_id)
    if app_res:
        await ver_msg.edit_text(
            f"{ver_res.reason}\n\n"
            f"🎉 <b>Төлем автоматты түрде қабылданды!</b>\n"
            f"📦 Пакет: <b>{tariff['title']}</b>\n"
            f"➕ Қосылды: <b>+{ver_res.credits_to_add} презентация</b>\n"
            f"🎫 Жалпы балансыңыз: <b>{app_res['new_credits']} презентация</b>\n\n"
            f"Енді презентация тақырыбын жаза беріңіз немесе құжат жіберіңіз!"
        )

        if app_res.get("partner_reward_kzt", 0) > 0 and app_res.get("referrer_id"):
            try:
                await bot.send_message(
                    chat_id=app_res["referrer_id"],
                    text=(
                        f"💸 <b>СЕРІКТЕСТІК БОНУС ЕСЕПТЕЛДІ!</b>\n\n"
                        f"Сіз шақырған достардың саудасы <b>{app_res['referrer_sales_total']:,} ₸</b>-ге жетті "
                        f"(Шақырылғандар: {app_res['referrer_invited_total']} адам)!\n"
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


# ----------------- Document Upload Handler (Kaspi Receipt OR Document-to-Slide) -----------------

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

    # 1. If seller is not set yet and a PDF is sent (e.g. Admin sending 1st receipt), or user is in payment mode
    lower_fname = filename.lower()
    is_receipt_filename = any(w in lower_fname for w in ("kaspi", "чек", "квитанц", "түбіртек", "receipt", "check"))
    if ext == ".pdf":
        if not get_seller_setting() and (not config.ADMIN_IDS or uid in config.ADMIN_IDS):
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
            + build_topic_ready_text(session, user_credits=get_user_credits(uid))
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
        r"^(\d{1,2})\s*(бет|слайд|беттік|слайдтан)(\s+болсын|\s+жаса|\s+қыл)?$", text, re.IGNORECASE
    )
    if only_slide_match:
        num = max(config.MIN_SLIDE_COUNT, min(int(only_slide_match.group(1)), config.MAX_SLIDE_COUNT))
        session.slideCount = num
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

    if inline_count:
        await execute_generation(bot, chat_id, session, user_id=uid)
        return

    card_text = build_topic_ready_text(session, user_credits=get_user_credits(uid))
    card_kb = build_topic_ready_keyboard(session)
    await message.answer(card_text, reply_markup=dict_to_inline_markup(card_kb))


# ----------------- Callback Handlers -----------------

@router.callback_query()
async def handle_callback(callback: CallbackQuery, bot: Bot):
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

    # Admin Refresh Dashboard
    if data == "admin_refresh":
        if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return

        text, pend_w = format_admin_dashboard_text()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(build_admin_keyboard(pend_w)))
            await callback.answer("Жаңартылды!")
        except Exception:
            await callback.answer()
        return

    # Admin Open Kaspi Pay & Seller Settings
    if data == "admin_kaspi_settings":
        if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        await callback.answer()
        text, kb = get_admin_kaspi_settings_message()
        try:
            await callback.message.edit_text(text, reply_markup=dict_to_inline_markup(kb))
        except Exception:
            await callback.message.answer(text, reply_markup=dict_to_inline_markup(kb))
        return

    # Admin Reset Seller Company (so next PDF receipt sets the new seller)
    if data == "admin_reset_seller":
        if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
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
        if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
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
        if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
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
                f"👥 Шақырған достары: <b>{w.get('invited_count', 0)} адам</b>\n"
                f"🛍 Реферал саудасы: <b>{w.get('referral_sales_kzt', 0):,} ₸</b>\n"
                f"💰 Қазіргі балансы: <b>{w.get('partner_balance_kzt', 0):,} ₸</b>\n\n"
                f"💵 <b>Төленетін сома: {w['amount_kzt']:,} ₸</b>\n"
                f"💳 <b>Реквизит:</b> <code>{w['requisites']}</code>"
            )
            kb = dict_to_inline_markup(build_admin_withdrawal_action_keyboard(w["id"], w["amount_kzt"]))
            await callback.message.answer(w_text, reply_markup=kb)
        return

    # Admin Click "✅ Төленді" on Partner Withdrawal
    if data.startswith("pay_withdraw:"):
        if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
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
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💵 Төленген сома: <b>{w_res['amount_kzt']:,} ₸</b>\n"
                    f"💳 Реквизит: <code>{w_res['requisites']}</code>\n"
                    f"💰 Қалған серіктестік балансыңыз: <b>{w_res['new_balance']:,} ₸</b>\n\n"
                    f"Бізбен бірге жұмыс істегеніңізге рақмет! Достар шақырып, табысыңызды арттыра беріңіз 🚀"
                ),
            )
        except Exception:
            pass
        return

    # Admin Reject Partner Withdrawal
    if data.startswith("reject_withdraw:"):
        if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
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

        try:
            await bot.send_message(
                chat_id=w_rej["user_id"],
                text=(
                    f"⚠️ <b>Сіздің #{w_id} ({w_rej['amount_kzt']:,} ₸) шығару сұранысыңыз қайтарылды.</b>\n"
                    f"Қаражат серіктестік балансыңызда сақталды. Реквизитіңізді тексеріп, қайта сұраныс жіберіңіз немесе админге жазыңыз."
                ),
            )
        except Exception:
            pass
        return

    # Admin View Recent Payments
    if data == "admin_payments":
        if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return

        await callback.answer()
        pays = get_recent_payments(10)
        if not pays:
            await callback.message.answer("🧾 Әзірге төлем чектері тіркелмеген.")
            return

        lines = ["🧾 <b>СОҢҒЫ 10 ТӨЛЕМ ЧЕКТЕРІ:</b>\n"]
        for p in pays:
            u_name = f"@{p['username']}" if p.get("username") else (p.get("first_name") or str(p["user_id"]))
            st_icon = "✅" if p["status"] == "approved" else ("⏳" if p["status"] == "pending" else "❌")
            r_no = p.get("receipt_number") or "PDF"
            lines.append(
                f"{st_icon} <b>#{p['id']}</b> • {u_name} (<code>{p['user_id']}</code>)\n"
                f"   💵 {p['amount_kzt']:,} ₸ (+{p['credits_added']} през) • Чек: <code>{r_no}</code>"
            )
        await callback.message.answer("\n".join(lines))
        return

    # Admin View Specific User Card
    if data.startswith("adm_view_user:"):
        if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        target_uid = int(data.split(":")[1])
        prof = get_user_profile(target_uid)
        await callback.answer()
        await callback.message.answer(
            format_user_admin_card(prof),
            reply_markup=dict_to_inline_markup(build_admin_user_manage_keyboard(target_uid)),
        )
        return

    # Admin 1-Tap Modify User Credits
    if data.startswith("adm_cred:"):
        if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
            await callback.answer("Рұқсат жоқ", show_alert=True)
            return
        parts = data.split(":")
        target_uid = int(parts[1])
        delta = int(parts[2])
        new_bal = add_user_credits(target_uid, delta)
        prof = get_user_profile(target_uid)
        await callback.answer(f"Баланс өзгертілді: {new_bal} през!")
        try:
            await callback.message.edit_text(
                format_user_admin_card(prof),
                reply_markup=dict_to_inline_markup(build_admin_user_manage_keyboard(target_uid)),
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
        await callback.answer()
        text, kb = get_payment_instruction_message(tariff_id)
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

    # Export Speaker Defense Script
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
        preview_lines = full_text.split("\n")[:14]
        preview_str = "\n".join(preview_lines)
        if len(preview_str) > 850:
            preview_str = preview_str[:850] + "..."

        caption = (
            f"{preview_str}\n\n"
            f"📥 Барлық {session.lastPresentation.slide_count} слайдтың толық қорғау сөзі жоғарыдағы Word (.DOCX) файлында!"
        )
        doc = BufferedInputFile(docx_bytes, filename=filename)
        await bot.send_document(chat_id=chat_id, document=doc, caption=caption, parse_mode=None)
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

    # Load Saved Project
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
            text = build_topic_ready_text(session, user_credits=get_user_credits(user_id))
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
            text = build_topic_ready_text(session, user_credits=get_user_credits(user_id))
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
        text = build_topic_ready_text(session, user_credits=get_user_credits(user_id))
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
                BotCommand(command="referral", description="👥 Реферал және Табыс табу"),
                BotCommand(command="projects", description="📂 Менің жобаларым"),
                BotCommand(command="support", description="👨‍💻 Админмен байланыс"),
                BotCommand(command="status", description="🏢 Компания статусы"),
                BotCommand(command="reset", description="🔄 Компанияны қайта орнату (Админ)"),
                BotCommand(command="admin", description="📊 Әкімші панелі"),
            ]
        )
    except Exception as e:
        logger.warning(f"Could not initialize bot metadata: {e}")

    logger.info(f"🤖 AI Presentation Telegram Bot (@{BOT_USERNAME_CACHE}) started successfully!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
