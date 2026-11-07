"""
Command & Menu Message Builders for AI Presentation Bot.
"""
from typing import Dict, Any, Tuple
import config
from app.core.themes import get_selected_theme_label
from app.core.db import (
    get_user_profile,
    get_dynamic_tariffs,
    get_kaspi_pay_url,
    get_seller_setting,
)
from app.bot.session import get_telegram_session
from app.bot.keyboards.reply import get_persistent_reply_keyboard
from app.bot.keyboards.inline import (
    build_clean_themes_keyboard,
    build_default_slides_keyboard,
    build_tariffs_keyboard,
    build_payment_instruction_keyboard,
    build_referral_keyboard,
    build_support_contact_keyboard,
    build_admin_kaspi_settings_keyboard,
    build_admin_price_editor_keyboard,
)


def get_start_message(chat_id: int, is_new: bool = False) -> Tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    profile = get_user_profile(chat_id)
    credits = profile.get("credits", 0)

    bonus_banner = (
        f"🎁 <b>Сізге тіркелгеніңіз үшін {config.WELCOME_FREE_CREDITS} ТЕГІН презентация берілді!</b>\n\n"
        if is_new
        else ""
    )

    text = (
        f"👋 Сәлем! Мен кәсіби <b>AI Presentation Bot</b>-пын.\n\n"
        f"{bonus_banner}"
        f"📌 <b>Қалай қолдануға болады?</b>\n"
        f"• Кез келген тақырыпты жазыңыз (мысалы: <i>«Жасанды интеллект»</i> немесе <i>«Қазақстан тарихы 10 бет»</i>).\n"
        f"• Немесе дайын <b>.PDF / .DOCX / .TXT</b> құжатын жіберіңіз — бот одан автоматты түрде слайд жасап береді!\n\n"
        f"🎫 <b>Сіздің балансыңыз:</b> <b>{credits} презентация</b>\n"
        f"⚙️ <b>Ағымдағы баптаулар:</b> {session.slideCount} слайд • {get_selected_theme_label(session.designId)}"
    )
    return text, get_persistent_reply_keyboard()


def get_tariffs_message(user_id: int) -> Tuple[str, Dict[str, Any]]:
    profile = get_user_profile(user_id)
    credits = profile.get("credits", 0)
    invited = profile.get("invited_count", 0)
    partner_bal = profile.get("partner_balance_kzt", 0)

    tariffs = get_dynamic_tariffs()
    t1 = tariffs["single"]
    t2 = tariffs["hit"]
    t3 = tariffs["vip"]

    partner_line = f"💰 Серіктестік табыс балансы: <b>{partner_bal:,} ₸</b>\n" if partner_bal > 0 else ""

    text = (
        f"💳 <b>БАЛАНС ЖӘНЕ ТАРИФТЕР</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎫 Қалған лимит: <b>{credits} презентация</b>\n"
        f"👥 Шақырған достарыңыз: <b>{invited} адам</b>\n"
        f"{partner_line}\n"
        f"📦 <b>Қолжетімді пакеттер (Kaspi Pay):</b>\n\n"
        f"1️⃣ <b>{t1['title']} — {t1['price_kzt']:,} ₸</b>\n"
        f"   • <b>{t1['credits']} презентация</b> + PDF + 🎤 Қорғау сөзі (Шпаргалка)\n"
        f"   • 30 дизайн стилін шексіз ауыстыру\n\n"
        f"2️⃣ 🔥 <b>{t2['title']} — {t2['price_kzt']:,} ₸</b>\n"
        f"   • <b>{t2['credits']} презентация</b> + барлық функциялар\n"
        f"   • Құжаттан слайд жасау (PDF / DOCX → Слайд)\n\n"
        f"3️⃣ 👑 <b>{t3['title']} — {t3['price_kzt']:,} ₸</b>\n"
        f"   • <b>{t3['credits']} презентация</b> + барлық функциялар\n"
        f"   • Топпен немесе сессия бойы қолдануға ең тиімді!\n\n"
        f"👇 Өзіңізге ыңғайлы пакетті таңдаңыз:"
    )
    return text, build_tariffs_keyboard()


def get_payment_instruction_message(tariff_id: str) -> Tuple[str, Dict[str, Any]]:
    """
    Strictly Kaspi Pay Link payment instruction (NO phone transfer).
    """
    tariffs = get_dynamic_tariffs()
    tariff = tariffs.get(tariff_id, tariffs["hit"])
    price = tariff["price_kzt"]
    title = tariff["title"]
    credits = tariff["credits"]

    pay_url = get_kaspi_pay_url()
    seller = get_seller_setting()

    company_line = f"🏢 Компания: <b>{seller['company']}</b>\n" if (seller and seller.get("company")) else ""
    pay_link_line = (
        f"🔗 <b>Kaspi Pay сілтемесі:</b> <a href='{pay_url}'>{pay_url}</a>\n\n"
        if pay_url and pay_url.startswith("http")
        else ""
    )

    text = (
        f"🔴 <b>KASPI PAY АРҚЫЛЫ ТӨЛЕУ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Пакет: <b>{title}</b> (+{credits} презентация)\n"
        f"💳 Төлем сомасы: <b>{price:,} ₸</b>\n"
        f"{company_line}\n"
        f"{pay_link_line}"
        f"✅ <b>Автоматты растау қадамдары:</b>\n"
        f"1. Төмендегі <b>«🔴 Kaspi Pay арқылы төлеу»</b> батырмасын басып, дәл <b>{price:,} ₸</b> төлеңіз.\n"
        f"2. Төлем өткен соң <b>PDF фискалдық чекті</b> осы чатқа жіберіңіз.\n"
        f"3. Бот чекті автоматты түрде тексеріп, балансыңызға сол сәтте <b>+{credits} презентация</b> қосады!"
    )
    return text, build_payment_instruction_keyboard(tariff_id)


def get_admin_kaspi_settings_message() -> Tuple[str, Dict[str, Any]]:
    """Formats the Admin Kaspi Pay & Seller Company status screen (matching test.py /status & /reset)."""
    seller = get_seller_setting()
    pay_url = get_kaspi_pay_url()

    if seller:
        seller_block = (
            f"🏢 Сақталған компания: <b>{seller.get('company')}</b>\n"
            f"🔢 ЖСН/БСН: <code>{seller.get('company_bin')}</code>\n"
            f"📄 Үлгі чек: <code>{seller.get('sample_receipt') or '—'}</code>\n"
        )
    else:
        seller_block = (
            "⚠️ <b>Компания әлі сақталмаған!</b>\n"
            "👉 Дәл қазір чатқа <b>алғашқы PDF чекті</b> жіберіңіз — бот компания атауы мен ЖСН/БСН-ды автоматты түрде есте сақтайды!\n"
        )

    text = (
        "🏢 <b>KASPI PAY ЖӘНЕ ФИСКАЛДЫҚ ЧЕК БАПТАУЛАРЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{seller_block}\n"
        f"🔗 <b>Ағымдағы Kaspi Pay сілтемесі:</b>\n"
        f"<code>{pay_url}</code>\n\n"
        "💡 <b>Қалай жұмыс істейді?</b>\n"
        "• Kaspi Pay сілтемесін кез келген уақытта төмендегі батырмамен өзгерте аласыз.\n"
        "• Басқа ИП / Kaspi Pay-ге ауысқанда <b>«🔄 Компанияны жаңа чекпен орнату»</b> (немесе <code>/reset</code>) басып, жаңа PDF чекті жіберсеңіз болды — бот жаңа компанияны өзі жаттап алады!"
    )
    return text, build_admin_kaspi_settings_keyboard()


def get_admin_price_editor_message() -> Tuple[str, Dict[str, Any]]:
    """Formats the Admin dynamic tariff price editor screen."""
    tariffs = get_dynamic_tariffs()
    t1 = tariffs["single"]
    t2 = tariffs["hit"]
    t3 = tariffs["vip"]

    text = (
        "💰 <b>ТАРИФ БАҒАЛАРЫН БАСҚАРУ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Қазіргі белсенді бағалар:\n"
        f"1️⃣ <b>{t1['title']}</b>: <b>{t1['price_kzt']:,} ₸</b> ({t1['credits']} презентация)\n"
        f"2️⃣ <b>{t2['title']}</b>: <b>{t2['price_kzt']:,} ₸</b> ({t2['credits']} презентация)\n"
        f"3️⃣ <b>{t3['title']}</b>: <b>{t3['price_kzt']:,} ₸</b> ({t3['credits']} презентация)\n\n"
        "👇 Өзгерткіңіз келетін тарифті басып, жаңа бағаны жазыңыз:"
    )
    return text, build_admin_price_editor_keyboard()


def get_referral_message(user_id: int, bot_username: str) -> Tuple[str, Dict[str, Any]]:
    profile = get_user_profile(user_id)
    invited = profile.get("invited_count", 0)
    sales_kzt = profile.get("referral_sales_kzt", 0)
    partner_bal = profile.get("partner_balance_kzt", 0)
    partner_total = profile.get("partner_total_earned_kzt", 0)

    clean_username = bot_username.lstrip("@") or "ai_presentation_bot"
    ref_link = f"https://t.me/{clean_username}?start=ref_{user_id}"

    friends_until_free = config.REFERRAL_FRIENDS_FOR_FREE_SLIDE - (invited % config.REFERRAL_FRIENDS_FOR_FREE_SLIDE)

    text = (
        f"👥 <b>РЕФЕРАЛДЫҚ ЖӘНЕ СЕРІКТЕСТІК БАҒДАРЛАМА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 <b>1-деңгей: Тегін презентация алу</b>\n"
        f"• Әр шақырған <b>2 досыңыз</b> үшін сізге автоматты түрде <b>+1 ТЕГІН презентация</b> беріледі!\n"
        f"• Келесі тегін презентацияға дейін: <b>{friends_until_free} дос</b> қалды.\n\n"
        f"💸 <b>2-деңгей: Студенттерге табыс табу (20% Кэшбэк)</b>\n"
        f"• Егер ботқа <b>20 адамнан көп</b> шақырсаңыз және олар жалпы <b>10 000 ₸</b> сауда жасаса — сізге <b>2 000 ₸ таза табыс</b> есептеледі!\n"
        f"• Жиналған табысты <b>кез келген сомада (минималды 2 000 ₸)</b> Kaspi нөміріңізге немесе картаңызға шығарып ала аласыз!\n\n"
        f"📊 <b>Сіздің көрсеткіштеріңіз:</b>\n"
        f"• Шақырылған достар: <b>{invited} / {config.PARTNER_MIN_INVITED_USERS} адам</b>\n"
        f"• Достардың саудасы: <b>{sales_kzt:,} / {config.PARTNER_SALES_THRESHOLD_KZT:,} ₸</b>\n"
        f"• 💰 <b>Шығаруға қолжетімді баланс: {partner_bal:,} ₸</b> (Жалпы тапқаныңыз: {partner_total:,} ₸)\n\n"
        f"🔗 <b>Сіздің жеке шақыру сілтемеңіз:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👇 Достарыңызға жіберу немесе табысты Kaspi-ге шығару:"
    )
    return text, build_referral_keyboard(ref_link, partner_bal)


def get_support_message(user_id: int) -> Tuple[str, Dict[str, Any]]:
    adm_line = ""
    if config.ADMIN_CONTACT:
        clean_adm = config.ADMIN_CONTACT.lstrip("@").replace("https://t.me/", "").strip()
        if clean_adm:
            adm_line = f"📱 Тікелей байланыс: @{clean_adm}\n"

    text = (
        f"👨‍💻 <b>АДМИНМЕН БАЙЛАНЫС ЖӘНЕ ҚОЛДАУ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Сұрағыңыз, ұсынысыңыз немесе төлем/серіктестік бойынша мәселе туындаса, "
        f"бізге кез келген уақытта жаза аласыз!\n\n"
        f"{adm_line}"
        f"🆔 Сіздің Telegram ID-іңіз: <code>{user_id}</code>\n\n"
        f"👇 Төмендегі <b>«✍️ Бот арқылы админге хабарлама жіберу»</b> батырмасын басып, "
        f"өз хабарламаңызды жазыңыз — әкімші сізге осы бот арқылы жауап береді:"
    )
    return text, build_support_contact_keyboard()


def get_help_message() -> Tuple[str, Dict[str, Any]]:
    help_text = (
        "ℹ️ <b>Бот мүмкіндіктері мен нұсқаулық:</b>\n\n"
        "1. <b>Тақырып бойынша жасау:</b> Чатқа презентация тақырыбын жазып, бет санын таңдаңыз.\n"
        "2. <b>Құжаттан слайд жасау (PDF / DOCX / TXT):</b> Чатқа реферат, мақала немесе есеп файлын жіберсеңіз, бот оның мазмұнынан дайын презентация құрастырады.\n"
        "3. <b>🎤 Қорғау сөзі (Шпаргалка):</b> Дайын презентацияның астындағы батырма арқылы әр слайдты қорғағанда айтатын дайын сөйлеу мәтінін (.DOCX) ала аласыз.\n"
        "4. <b>📂 Менің жобаларым:</b> Бұрын жасаған барлық презентацияларыңыз сақталады — кез келген уақытта қайта жүктей аласыз.\n"
        "5. <b>👥 Реферал және Табыс:</b> 2 дос шақырып +1 тегін презентация алыңыз, ал 20+ дос пен 10 000 ₸ саудадан 2 000 ₸ табыс тауып, Kaspi-ге шығарып алыңыз!\n"
        "6. <b>👨‍💻 Админмен байланыс:</b> Кез келген сұрақ бойынша әкімшіге тікелей хабарлама жіберіңіз."
    )
    return help_text, get_persistent_reply_keyboard()


def get_slides_message(chat_id: int) -> Tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    text = f"📄 Неше беттік презентация жасағыңыз келеді? (Қазір: {session.slideCount} бет):"
    return text, build_default_slides_keyboard(session, is_regenerate=False)


def get_design_message(chat_id: int) -> Tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    mode = "topic" if session.pendingTopic else "default"
    text = f"🎨 30 кәсіби дизайн шаблонынан таңдаңыз (Қазір: {get_selected_theme_label(session.designId, session.pendingTopic)}):"
    return text, build_clean_themes_keyboard(session, session.themePage, mode)
