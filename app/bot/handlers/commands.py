"""
Command & Menu Message Builders for AI Presentation Bot (Commercial Pro v2 Edition).
"""
from typing import Dict, Any, Tuple, Optional
import config
from app.core.themes import get_selected_theme_label
from app.core.db import (
    get_user_profile,
    get_user_credit_breakdown,
    get_dynamic_tariffs,
    get_kaspi_pay_url,
    get_seller_setting,
    get_user_active_promo,
    get_enabled_generation_modes,
)
from app.bot.session import get_telegram_session
from app.bot.keyboards.reply import get_persistent_reply_keyboard
from app.bot.keyboards.inline import (
    build_clean_themes_keyboard,
    build_default_slides_keyboard,
    build_templates_keyboard,
    build_tariffs_keyboard,
    build_payment_instruction_keyboard,
    build_referral_keyboard,
    build_support_contact_keyboard,
    build_admin_kaspi_settings_keyboard,
    build_admin_price_editor_keyboard,
    build_admin_gen_modes_keyboard,
)


def get_start_message(chat_id: int, is_new: bool = False, streak_days: int = 1, streak_bonus: bool = False) -> Tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    b = get_user_credit_breakdown(chat_id)
    lang_info = config.SUPPORTED_LANGUAGES.get(session.language, config.SUPPORTED_LANGUAGES["қазақша"])
    tmpl_info = config.TEMPLATE_LIBRARY.get(session.templateId, config.TEMPLATE_LIBRARY["standard"])

    bonus_banner = (
        f"🎁 <b>Сізге тіркелгеніңіз үшін {config.WELCOME_FREE_CREDITS} ТЕГІН презентация («Бір реттік» немесе «Бір реттік + ФОТО» үшін) берілді!</b>\n\n"
        if is_new
        else ""
    )

    streak_banner = (
        f"🔥 <b>3 күн қатарынан кіргеніңіз үшін +1 ТЕГІН презентация қосылды!</b> (Стрик: {streak_days} күн)\n\n"
        if streak_bonus
        else f"🔥 <b>Күнделікті стрик:</b> {streak_days} күн (3 күн қатарынан кірсеңіз → +1 тегін презентация!)\n"
    )

    text = (
        f"👋 Сәлем! Мен кәсіби <b>AI Presentation Bot Pro</b>-мын.\n\n"
        f"{bonus_banner}"
        f"📌 <b>Қалай қолдануға болады?</b>\n"
        f"• Кез келген тақырыпты жазыңыз — бот бірден <b>3 дайын файлды (.PPTX + .PDF + .DOCX Қорғау сөзі)</b> жібереді!\n"
        f"• Немесе дайын <b>.PDF / .DOCX / .TXT</b> құжатын жіберіңіз.\n"
        f"• <b>📐 8 Академиялық & Бизнес үлгі:</b> Диплом қорғау, Ғылыми, Медициналық, Заң жобасы, Маркетинг, Экология, Сабақ жоспары, Бизнес-жоспар.\n"
        f"• <b>🚀 Инлайн-режим:</b> Кез келген чатта <code>@бот_аты тақырып</code> деп жазып, достарыңызбен бөлісе аласыз!\n\n"
        f"{streak_banner}"
        f"🎫 <b>Сіздің балансыңыз (Барлығы: {b['total']} през):</b>\n"
        f"   • 🎁 Тегін бонус: <b>{b['bonus']}</b> (Фотосыз / Фотомен жарайды)\n"
        f"   • 📄 Фотосыз: <b>{b['no_photo']}</b> | 🖼 Фотомен: <b>{b['ddg_photo']}</b> | ✨ OpenAI: <b>{b['openai_photo']}</b>\n"
        f"⚙️ <b>Баптаулар:</b> {session.slideCount} слайд • {tmpl_info['title']} • {lang_info['short']}"
    )
    return text, get_persistent_reply_keyboard()


def get_tariffs_message(user_id: int) -> Tuple[str, Dict[str, Any]]:
    profile = get_user_profile(user_id)
    b = get_user_credit_breakdown(user_id)
    invited = profile.get("invited_count", 0)
    partner_bal = profile.get("partner_balance_kzt", 0)
    streak_days = profile.get("streak_days", 1)

    tariffs = get_dynamic_tariffs(user_id=user_id)
    promo = get_user_active_promo(user_id)
    promo_banner = (
        f"🏷 <b>Белсенді промокод: «{promo['code']}» (тек «Бір реттік» пакеттерге -{promo['discount_percent']}% жеңілдік есептелді!)</b>\n\n"
        if promo
        else "💡 <i>Промокод (мысалы: <code>ALASH2025</code> немесе <code>KAZNU50</code>) болса, «Бір реттік» пакеттерге -50% жеңілдік алыңыз!</i>\n\n"
    )

    partner_line = f"💰 Серіктестік табыс балансы: <b>{partner_bal:,} ₸</b>\n" if partner_bal > 0 else ""

    pkg_lines = []
    for idx, (k, t) in enumerate(tariffs.items(), 1):
        np_c = int(t.get("no_photo_credits", 0))
        ddg_c = int(t.get("ddg_photo_credits", 0))
        oai_c = int(t.get("openai_photo_credits", 0))
        if t["credits"] == 1:
            if oai_c > 0:
                detail = "1 презентация (OpenAI <code>gpt-image-2</code> AI фотомен)"
            elif ddg_c > 0:
                detail = "1 презентация (интернеттен мысал фотомен — ЖИ қателесуі мүмкін, PPTX-те ауыстыруға болады)"
            else:
                detail = "1 презентация (фотосыз)"
        else:
            detail = f"<b>{t['credits']} презентация</b> (<b>{np_c}</b> фотосыз + <b>{ddg_c}</b> фотомен + <b>{oai_c}</b> OpenAI)"
        orig_p = t.get("original_price_kzt")
        price_str = f"<s>{orig_p:,} ₸</s> → <b>{t['price_kzt']:,} ₸ (-{t.get('discount_percent')}%)</b>" if (orig_p and orig_p != t["price_kzt"]) else f"<b>{t['price_kzt']:,} ₸</b>"
        pkg_lines.append(f"{idx}️⃣ <b>{t['title']}</b> — {price_str}\n   • {detail}")

    pkgs_block = "\n\n".join(pkg_lines)

    text = (
        f"💳 <b>БАЛАНС ЖӘНЕ ТАРИФТЕР</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎫 <b>Жалпы лимит: {b['total']} презентация</b>\n"
        f"   • 🎁 Тегін бонус: <b>{b['bonus']}</b> («Бір реттік» және «Бір реттік + ФОТО» үшін)\n"
        f"   • 📄 Фотосыз: <b>{b['no_photo']}</b> | 🖼 Фотомен: <b>{b['ddg_photo']}</b> | ✨ OpenAI: <b>{b['openai_photo']}</b>\n"
        f"🔥 Күнделікті стрик: <b>{streak_days} күн</b> (3 күн = +1 тегін през)\n"
        f"👥 Шақырған достарыңыз: <b>{invited} адам</b>\n"
        f"{partner_line}\n"
        f"{promo_banner}"
        f"📦 <b>Қолжетімді пакеттер (Kaspi Pay):</b>\n\n"
        f"{pkgs_block}\n\n"
        f"👇 Өзіңізге ыңғайлы пакетті таңдаңыз:"
    )
    return text, build_tariffs_keyboard(user_id=user_id)


def get_payment_instruction_message(tariff_id: str, user_id: Optional[int] = None) -> Tuple[str, Dict[str, Any]]:
    tariffs = get_dynamic_tariffs(user_id=user_id)
    tariff = tariffs.get(tariff_id, next(iter(tariffs.values())) if tariffs else config.TARIFF_PLANS["single"])
    price = tariff["price_kzt"]
    orig_price = tariff.get("original_price_kzt")
    title = tariff["title"]
    credits = tariff["credits"]
    np_c = int(tariff.get("no_photo_credits", 0))
    ddg_c = int(tariff.get("ddg_photo_credits", 0))
    oai_c = int(tariff.get("openai_photo_credits", 0))

    pay_url = get_kaspi_pay_url()
    seller = get_seller_setting()

    discount_line = (
        f"🏷 1-реттік жеңілдікпен: <s>{orig_price:,} ₸</s> → <b>{price:,} ₸</b> (Промокод: <code>{tariff.get('promo_code')}</code>)\n"
        if orig_price and orig_price != price
        else f"💳 Төлем сомасы: <b>{price:,} ₸</b>\n"
    )
    split_badge = f" ({np_c} фотосыз + {ddg_c} фотомен + {oai_c} OpenAI)"

    ddg_warn = f"\n{config.DDG_PHOTO_WARNING_TEXT}\n" if ddg_c > 0 and oai_c == 0 else ""
    company_line = f"🏢 Компания: <b>{seller['company']}</b>\n" if (seller and seller.get("company")) else ""
    pay_link_line = (
        f"🔗 <b>Kaspi Pay сілтемесі:</b> <a href='{pay_url}'>{pay_url}</a>\n\n"
        if pay_url and pay_url.startswith("http")
        else ""
    )

    text = (
        f"🔴 <b>KASPI PAY АРҚЫЛЫ ТӨЛЕУ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Пакет: <b>{title}</b> (+{credits} презентация{split_badge})\n"
        f"{discount_line}"
        f"{company_line}"
        f"{ddg_warn}\n"
        f"{pay_link_line}"
        f"✅ <b>Автоматты растау қадамдары:</b>\n"
        f"1. Төмендегі <b>«🔴 Kaspi Pay арқылы төлеу»</b> батырмасын басып, дәл <b>{price:,} ₸</b> төлеңіз.\n"
        f"2. Төлем өткен соң <b>PDF фискалдық чекті</b> осы чатқа жіберіңіз.\n"
        f"3. Бот чекті автоматты түрде тексеріп (немесе авто-тексеру өтпесе, админ қолмен растап), балансыңызға сол сәтте <b>+{credits} презентация</b> қосады!"
    )
    return text, build_payment_instruction_keyboard(tariff_id, user_id=user_id)


def get_admin_kaspi_settings_message() -> Tuple[str, Dict[str, Any]]:
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
        f"<code>{pay_url}</code>"
    )
    return text, build_admin_kaspi_settings_keyboard()


def get_admin_price_editor_message() -> Tuple[str, Dict[str, Any]]:
    tariffs = get_dynamic_tariffs(include_disabled=True)
    lines = [
        "💰 <b>ТАРИФТІК ПАКЕТТЕРДІ БАСҚАРУ (ҚОСУ / ӨЗГЕРТУ / ӨШІРУ)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <i>Кез келген пакетті «🔴 Өшіру» батырмасымен уақытша өшіріп, қалаған кезде «🟢 Қайта қосу» арқылы қайта қоса аласыз!</i>\n"
    ]
    for idx, (k, t) in enumerate(tariffs.items(), 1):
        np_c = int(t.get("no_photo_credits", 0))
        ddg_c = int(t.get("ddg_photo_credits", 0))
        oai_c = int(t.get("openai_photo_credits", 0))
        is_en = t.get("is_enabled", True)
        st_lbl = "🟢 ҚОСУЛЫ" if is_en else "🔴 ӨШІРУЛІ (Клиенттерге көрінбейді)"
        lines.append(
            f"{idx}. <b>{t['title']}</b> — <b>{t['price_kzt']:,} ₸</b> [{st_lbl}]\n"
            f"   Барлығы: {t['credits']} през ({np_c} фотосыз / {ddg_c} фотомен / {oai_c} OpenAI)"
        )
    lines.append("\n👇 Пакет бағасын өзгертіңіз, жаңа пакет қосыңыз немесе пакетті өшіріп/қосыңыз:")
    return "\n".join(lines), build_admin_price_editor_keyboard()


def get_admin_gen_modes_message() -> Tuple[str, Dict[str, Any]]:
    modes = get_enabled_generation_modes()
    m_none = modes.get("none", True)
    m_ddg = modes.get("ddg", True)
    m_oai = modes.get("gpt-image-2", True)

    lines = [
        "🎛 <b>3 ПРЕЗЕНТАЦИЯ ТҮРІН БАСҚАРУ (ҚОСУ / ӨШІРУ)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Қолданушыларға презентация жасаудың қай түрлері қолжетімді болатынын осы жерден басқара аласыз:\n\n"
        f"1️⃣ <b>🚫 Фотосыз («Бір реттік»):</b> {'🟢 ҚОСУЛЫ' if m_none else '🔴 ӨШІРУЛІ'}\n"
        f"2️⃣ <b>🖼 Фотомен (Интернет/ЖИ):</b> {'🟢 ҚОСУЛЫ' if m_ddg else '🔴 ӨШІРУЛІ'}\n"
        f"3️⃣ <b>✨ OpenAI Фотомен (gpt-image-2):</b> {'🟢 ҚОСУЛЫ' if m_oai else '🔴 ӨШІРУЛІ'}\n\n"
        "💡 <i>Мысалы: «📄 Тек Фотосыз қалдыру» батырмасын бассаңыз, фотомен жасау түрлері өшіріліп, тек фотосыз презентация жасау қалады. Ал «🔄 Барлық 3 түрді қосу» арқылы бәрін қайта қоса аласыз!</i>"
    ]
    return "\n".join(lines), build_admin_gen_modes_keyboard()


def get_referral_message(user_id: int, bot_username: str) -> Tuple[str, Dict[str, Any]]:
    profile = get_user_profile(user_id)
    invited = profile.get("invited_count", 0)
    sales_kzt = profile.get("referral_sales_kzt", 0)
    partner_bal = profile.get("partner_balance_kzt", 0)
    partner_total = profile.get("partner_total_earned_kzt", 0)
    streak_days = profile.get("streak_days", 1)

    clean_username = bot_username.lstrip("@") or "ai_presentation_bot"
    ref_link = f"https://t.me/{clean_username}?start=ref_{user_id}"

    friends_until_free = config.REFERRAL_FRIENDS_FOR_FREE_SLIDE - (invited % config.REFERRAL_FRIENDS_FOR_FREE_SLIDE)

    text = (
        f"👥 <b>РЕФЕРАЛДЫҚ ЖӘНЕ СЕРІКТЕСТІК БАҒДАРЛАМА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 <b>1-деңгей: Дос шақыру және 3-күндік Стрик бонусы</b>\n"
        f"• Әр шақырған <b>2 досыңыз</b> үшін сізге автоматты түрде <b>+1 ТЕГІН презентация</b> («Бір реттік» немесе «Бір реттік + ФОТО» үшін) беріледі! (Келесіге: {friends_until_free} дос)\n"
        f"• Ботқа <b>3 күн қатарынан</b> кірсеңіз — тағы <b>+1 ТЕГІН презентация</b> қосылады! (Қазіргі стрик: {streak_days} күн)\n\n"
        f"💸 <b>2-деңгей: Студенттерге табыс табу (20% Кэшбэк)</b>\n"
        f"• Егер ботқа <b>20 адамнан көп</b> шақырсаңыз және олар жалпы <b>10 000 ₸</b> сауда жасаса — сізге <b>2 000 ₸ таза табыс</b> есептеледі!\n"
        f"• Жиналған табысты <b>кез келген сомада (минималды 2 000 ₸)</b> Kaspi нөміріңізге немесе картаңызға шығарып ала аласыз!\n\n"
        f"📊 <b>Сіздің көрсеткіштеріңіз:</b>\n"
        f"• Шақырылған достар: <b>{invited} / {config.PARTNER_MIN_INVITED_USERS} адам</b>\n"
        f"• Достардың саудасы: <b>{sales_kzt:,} / {config.PARTNER_SALES_THRESHOLD_KZT:,} ₸</b>\n"
        f"• 💰 <b>Шығаруға қолжетімді баланс: {partner_bal:,} ₸</b> (Жалпы тапқаныңыз: {partner_total:,} ₸)\n\n"
        f"🔗 <b>Сіздің жеке шақыру сілтемеңіз:</b>\n"
        f"<code>{ref_link}</code>"
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
        f"Сұрағыңыз, университет серіктестігі, промокод немесе төлем бойынша мәселе туындаса, "
        f"бізге кез келген уақытта жаза аласыз!\n\n"
        f"{adm_line}"
        f"🆔 Сіздің Telegram ID-іңіз: <code>{user_id}</code>"
    )
    return text, build_support_contact_keyboard()


def get_help_message() -> Tuple[str, Dict[str, Any]]:
    help_text = (
        "ℹ️ <b>AI Presentation Bot Pro мүмкіндіктері:</b>\n\n"
        "1. <b>Бірден 3 файл (.PPTX + .PDF + .DOCX):</b> Тақырып жазсаңыз, презентация (.PPTX), телефоннан көруге арналған (.PDF) және спикердің Қорғау сөзі (.DOCX) бірден жіберіледі!\n"
        "2. <b>📐 8 Кәсіби & Академиялық Шаблон:</b> Диплом қорғау, Ғылыми баяндама, Медициналық баяндама, Заң жобасы, Маркетингтік стратегия, Экологиялық жоба, Сабақ жоспары, Бизнес-жоспар.\n"
        "3. <b>🖼 Фото режимдері:</b> Фотосыз (200 ₸), Интернеттен мысал фотомен (300 ₸) және OpenAI <code>gpt-image-2</code> AI фотомен (500 ₸ / Хит / Pro / VIP).\n"
        "4. <b>🌐 3 Тіл:</b> Қазақша 🇰🇿, Орысша 🇷🇺, Ағылшынша 🇬🇧.\n"
        "5. <b>🎟 1-реттік Промокодтар:</b> <code>ALASH2025</code>, <code>KAZNU50</code> арқылы 50% жеңілдік!"
    )
    return help_text, get_persistent_reply_keyboard()


def get_slides_message(chat_id: int) -> Tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    text = f"📄 Неше беттік презентация жасағыңыз келеді? (Қазір: {session.slideCount} бет):"
    return text, build_default_slides_keyboard(session, is_regenerate=False)


def get_design_message(chat_id: int) -> Tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    mode = "topic" if session.pendingTopic else "default"
    text = f"🎨 35 кәсіби дизайн шаблонынан таңдаңыз (Қазір: {get_selected_theme_label(session.designId, session.pendingTopic, with_photos=session.withPhotos)}):"
    return text, build_clean_themes_keyboard(session, session.themePage, mode)


def get_templates_message(chat_id: int) -> Tuple[str, Dict[str, Any]]:
    session = get_telegram_session(chat_id)
    mode = "topic" if session.pendingTopic else "default"
    tmpl = config.TEMPLATE_LIBRARY.get(session.templateId, config.TEMPLATE_LIBRARY["standard"])
    text = (
        f"📐 <b>ҮЛГІ (TEMPLATE) КІТАПХАНАСЫ</b>\n"
        f"Қазіргі таңдалған құрылым: <b>{tmpl['title']}</b>\n\n"
        f"Қажетті академиялық немесе кәсіби құрылымды таңдаңыз:"
    )
    return text, build_templates_keyboard(session, mode=mode)
