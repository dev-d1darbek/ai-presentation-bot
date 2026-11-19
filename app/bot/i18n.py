"""
Trilingual UI localization dictionary (kk: Қазақша, ru: Русский, en: English)
for SlideAI KZ Presentation Bot — Clean Minimal Modern UI/UX.
"""
from typing import Dict, Any

DIRECTIONS: Dict[str, Dict[str, str]] = {
    "standard": {
        "kk": "🎓 Академиялық",
        "ru": "🎓 Академическая",
        "en": "🎓 Academic",
        "title_kk": "🎓 Академиялық презентация",
        "title_ru": "🎓 Академическая презентация",
        "title_en": "🎓 Academic Presentation",
        "persona": "academic_universal",
    },
    "scientific": {
        "kk": "🔬 Ғылыми баяндама",
        "ru": "🔬 Научный доклад",
        "en": "🔬 Scientific Report",
        "title_kk": "🔬 Ғылыми баяндама",
        "title_ru": "🔬 Научный доклад",
        "title_en": "🔬 Scientific Report",
        "persona": "academic_universal",
    },
    "diploma": {
        "kk": "📜 Диплом қорғау",
        "ru": "📜 Защита диплома",
        "en": "📜 Thesis Defense",
        "title_kk": "📜 Диплом қорғау",
        "title_ru": "📜 Защита диплома",
        "title_en": "📜 Thesis Defense",
        "persona": "academic_universal",
    },
    "business": {
        "kk": "💼 Бизнес-жоспар",
        "ru": "💼 Бизнес-план",
        "en": "💼 Business Plan",
        "title_kk": "💼 Бизнес-жоспар",
        "title_ru": "💼 Бизнес-план",
        "title_en": "💼 Business Plan",
        "persona": "business_pitch",
    },
    "lesson": {
        "kk": "📚 Сабақ жоспары",
        "ru": "📚 План урока",
        "en": "📚 Lesson Plan",
        "title_kk": "📚 Сабақ жоспары",
        "title_ru": "📚 План урока",
        "title_en": "📚 Lesson Plan",
        "persona": "teacher_pedagogy",
    },
    "medical": {
        "kk": "🏥 Медицина",
        "ru": "🏥 Медицина",
        "en": "🏥 Medical",
        "title_kk": "🏥 Медициналық баяндама",
        "title_ru": "🏥 Медицинский доклад",
        "title_en": "🏥 Medical Report",
        "persona": "medical_science",
    },
    "law": {
        "kk": "⚖️ Заң жобасы",
        "ru": "⚖️ Законопроект",
        "en": "⚖️ Legal Project",
        "title_kk": "⚖️ Заң жобасы",
        "title_ru": "⚖️ Законопроект",
        "title_en": "⚖️ Legal Project",
        "persona": "academic_universal",
    },
    "marketing": {
        "kk": "📊 Маркетинг",
        "ru": "📊 Маркетинг",
        "en": "📊 Marketing",
        "title_kk": "📊 Маркетингтік стратегия",
        "title_ru": "📊 Маркетинговая стратегия",
        "title_en": "📊 Marketing Strategy",
        "persona": "business_pitch",
    },
    "ecology": {
        "kk": "🌍 Экология",
        "ru": "🌍 Экология",
        "en": "🌍 Ecology",
        "title_kk": "🌍 Экологиялық жоба",
        "title_ru": "🌍 Экологический проект",
        "title_en": "🌍 Ecological Project",
        "persona": "academic_universal",
    },
}


def norm_lang(ui_lang: str) -> str:
    l = str(ui_lang or "kk").lower().strip()
    if l in ("ru", "русский"):
        return "ru"
    if l in ("en", "english"):
        return "en"
    return "kk"


def get_dir_title(dir_id: str, ui_lang: str) -> str:
    l = norm_lang(ui_lang)
    d = DIRECTIONS.get(dir_id, DIRECTIONS["standard"])
    return d.get(f"title_{l}", d["title_kk"])


def get_dir_button(dir_id: str, ui_lang: str) -> str:
    l = norm_lang(ui_lang)
    d = DIRECTIONS.get(dir_id, DIRECTIONS["standard"])
    return d.get(l, d["kk"])


TEXTS: Dict[str, Dict[str, str]] = {
    "kk": {
        "btn_new": "✨ Жаңа презентация жасау",
        "btn_projects": "📂 Менің жобаларым",
        "btn_lang": "🌐 Тіл / Язык",
        "btn_balance": "💳 Баланс",
        "btn_support": "👨‍💻 Байланыс",
        "btn_admin": "⚙️ Админ",
        "lang_set_confirm": "✅ Бот тілі орнатылды: <b>Қазақша 🇰🇿</b>",
        "bot_brand": "✨ <b>SlideAI KZ</b>",
        "balance_line": "🎫 Баланс: <b>{total} презентация</b>",
        "choose_dir": "👇 Бағытты таңдаңыз:",
        "ask_topic": "<b>{dir_title}</b>\n\n✍️ Презентацияның тақырыбын жазыңыз:",
        "ask_pres_lang": "<b>{dir_title}</b>\n📌 Тақырып: <b>«{topic}»</b>\n\n🌐 Презентация тілін таңдаңыз:",
        "ask_slides": "<b>{dir_title}</b>\n📌 Тақырып: <b>«{topic}»</b>\n🌐 Тіл: {pres_lang}\n\n📄 Неше беттік презентация жасаймыз?",
        "ask_photo": "<b>{dir_title}</b>\n📌 Тақырып: <b>«{topic}»</b>\n🌐 Тіл: {pres_lang} • 📄 {count} бет\n\n🖼 <b>Фотомен бе, әлде фотосыз ба?</b>\n<i>Таңдасаңыз, генерация бірден басталады:</i>",
        "btn_no_photo": "🚫 Фотосыз",
        "btn_with_photo": "🖼 Фотомен",
        "slide_unit": "бет",
        "slide_word": "слайд",
        "btn_back": "⬅️ Артқа",
        "progress_preparing": "⏳ <b>«{topic}» дайындалуда...</b>\n\n<code>[▓▓▓▓▓▓▓▓▓░]</code> <b>95%</b>\n📦 Дайын файлдар (.PDF + .PPTX) жүктелуде...\n\n📄 {count} слайд • 🎨 {theme}",
        "pdf_caption": "📱 <b>Телефонда ашып көруге арналған нұсқа (.PDF)</b>",
        "pptx_caption": (
            "📊 <b>Негізгі презентация (.PPTX)</b>\n"
            "📌 <b>{topic}</b>\n"
            "📄 {count} слайд • {photo_badge}\n"
            "🎨 {theme}"
        ),
        "photo_badge_none": "🚫 Фотосыз",
        "photo_badge_with": "🖼 Фотомен",
        "btn_change_design": "🎨 Дизайн ауыстыру",
        "projects_empty": "📂 <b>Сақталған жобалар әзірге жоқ.</b>\n\n«✨ Жаңа презентация жасау» батырмасын басып бастаңыз!",
        "projects_header": "📂 <b>Сақталған жобаларым ({total}):</b>\n\n👇 Кез келген жобаны бассаңыз, бот <b>.PDF + .PPTX</b> қайта жібереді:",
        "balance_screen": (
            "💳 <b>Баланс: {total} презентация</b>\n\n"
            "💎 Бағасы: <b>1 презентация — {price} ₸</b> (Фотосыз / Фотомен)\n"
            "🧾 Kaspi Pay (PDF чекті жіберіңіз) немесе ⭐️ <b>Telegram Stars ({stars} ⭐️)</b> арқылы төлеңіз:"
        ),
        "btn_kaspi_pay": "🔴 Kaspi Pay ({price} ₸)",
        "btn_stars_pay": "⭐️ Telegram Stars ({stars} ⭐️)",
        "stars_title": "1 презентация (SlideAI KZ)",
        "stars_desc": "1 презентация генерациясы (Фотосыз / Фотомен)",
        "stars_success": "⭐️ <b>Telegram Stars төлемі сәтті өтті!</b>\n➕ Балансыңызға <b>+1 презентация</b> қосылды!",
        "kaspi_success": "✅ <b>+{credits} презентация қосылды!</b>\n🎫 Жалпы баланс: <b>{total} презентация</b>",
        "kaspi_error": "❌ <b>Қате: чек қабылданбады.</b>\nСұрақ туындаса, әкімшіге жазыңыз:",
        "btn_promo": "🎟 Промокод",
        "promo_prompt": "🎟 Промокодты немесе сыйлық кодын жазып жіберіңіз:\n<i>Бас тарту: /cancel</i>",
        "support_screen": (
            "👨‍💻 <b>Қолдау қызметі</b>\n\n"
            "Сұрағыңыз, промокод немесе төлем бойынша мәселе туындаса, кез келген уақытта жаза аласыз!\n\n"
            "📱 Тікелей байланыс: @{admin_user}\n"
            "🆔 Telegram ID: <code>{user_id}</code>"
        ),
        "btn_direct_admin": "📲 Тікелей админге жазу",
        "btn_bot_admin": "💬 Бот арқылы админге жазу",
        "support_prompt": "✍️ Әкімшіге жазатын сұрағыңызды немесе шағымыңызды жазыңыз:\n<i>Бас тарту: /cancel</i>",
        "support_sent": "✅ Хабарламаңыз әкімшіге жеткізілді! Жауабы осы чатқа келеді.",
        "topic_too_short": "⚠️ Тақырыпты толығырақ жазыңыз.",
        "not_enough_credits": "⚠️ Балансыңызда презентация қалмады. «💳 Баланс» бөлімі арқылы толықтырыңыз немесе промокод енгізіңіз.",
    },
    "ru": {
        "btn_new": "✨ Создать новую презентацию",
        "btn_projects": "📂 Мои проекты",
        "btn_lang": "🌐 Язык / Тіл",
        "btn_balance": "💳 Баланс",
        "btn_support": "👨‍💻 Поддержка",
        "btn_admin": "⚙️ Админ",
        "lang_set_confirm": "✅ Язык интерфейса установлен: <b>Русский 🇷🇺</b>",
        "bot_brand": "✨ <b>SlideAI KZ</b>",
        "balance_line": "🎫 Баланс: <b>{total} презентаций</b>",
        "choose_dir": "👇 Выберите направление:",
        "ask_topic": "<b>{dir_title}</b>\n\n✍️ Напишите тему презентации:",
        "ask_pres_lang": "<b>{dir_title}</b>\n📌 Тема: <b>«{topic}»</b>\n\n🌐 Выберите язык презентации:",
        "ask_slides": "<b>{dir_title}</b>\n📌 Тема: <b>«{topic}»</b>\n🌐 Язык: {pres_lang}\n\n📄 Сколько слайдов создать?",
        "ask_photo": "<b>{dir_title}</b>\n📌 Тема: <b>«{topic}»</b>\n🌐 Язык: {pres_lang} • 📄 {count} стр.\n\n🖼 <b>С фото или без фото?</b>\n<i>После выбора сразу начнется генерация:</i>",
        "btn_no_photo": "🚫 Без фото",
        "btn_with_photo": "🖼 С фото",
        "slide_unit": "стр.",
        "slide_word": "слайдов",
        "btn_back": "⬅️ Назад",
        "progress_preparing": "⏳ <b>«{topic}» готовится...</b>\n\n<code>[▓▓▓▓▓▓▓▓▓░]</code> <b>95%</b>\n📦 Загружаем готовые файлы (.PDF + .PPTX)...\n\n📄 {count} слайдов • 🎨 {theme}",
        "pdf_caption": "📱 <b>Версия для просмотра на телефоне (.PDF)</b>",
        "pptx_caption": (
            "📊 <b>Основная презентация (.PPTX)</b>\n"
            "📌 <b>{topic}</b>\n"
            "📄 {count} слайдов • {photo_badge}\n"
            "🎨 {theme}"
        ),
        "photo_badge_none": "🚫 Без фото",
        "photo_badge_with": "🖼 С фото",
        "btn_change_design": "🎨 Сменить дизайн",
        "projects_empty": "📂 <b>У вас пока нет сохраненных проектов.</b>\n\nНажмите «✨ Создать новую презентацию», чтобы начать!",
        "projects_header": "📂 <b>Мои сохраненные проекты ({total}):</b>\n\n👇 Нажмите на проект, чтобы получить <b>.PDF + .PPTX</b>:",
        "balance_screen": (
            "💳 <b>Баланс: {total} презентаций</b>\n\n"
            "💎 Стоимость: <b>1 презентация — {price} ₸</b> (Без фото / С фото)\n"
            "🧾 Оплатите через Kaspi Pay (отправьте PDF-чек) или ⭐️ <b>Telegram Stars ({stars} ⭐️)</b>:"
        ),
        "btn_kaspi_pay": "🔴 Kaspi Pay ({price} ₸)",
        "btn_stars_pay": "⭐️ Telegram Stars ({stars} ⭐️)",
        "stars_title": "1 презентация (SlideAI KZ)",
        "stars_desc": "1 презентация генерациясы (Фотосыз / Фотомен)",
        "stars_success": "⭐️ <b>Telegram Stars төлемі сәтті өтті!</b>\n➕ Балансыңызға <b>+1 презентация</b> қосылды!",
        "kaspi_success": "✅ <b>+{credits} презентация қосылды!</b>\n🎫 Жалпы баланс: <b>{total} презентация</b>",
        "kaspi_error": "❌ <b>Қате: чек қабылданбады.</b>\nСұрақ туындаса, әкімшіге жазыңыз:",
        "btn_promo": "🎟 Промокод",
        "promo_prompt": "🎟 Введите промокод или подарочный код:\n<i>Отмена: /cancel</i>",
        "support_screen": (
            "👨‍💻 <b>Служба поддержки</b>\n\n"
            "Если у вас есть вопросы по промокодам или оплате, напишите нам в любое время!\n\n"
            "📱 Прямая связь: @{admin_user}\n"
            "🆔 Telegram ID: <code>{user_id}</code>"
        ),
        "btn_direct_admin": "📲 Написать админу напрямую",
        "btn_bot_admin": "💬 Написать админу через бота",
        "support_prompt": "✍️ Напишите ваш вопрос или жалобу администратору:\n<i>Отмена: /cancel</i>",
        "support_sent": "✅ Ваше сообщение доставлено администратору! Ответ придет в этот чат.",
        "topic_too_short": "⚠️ Пожалуйста, введите тему подробнее.",
        "not_enough_credits": "⚠️ У вас закончились презентации. Пополните баланс в разделе «💳 Баланс» или введите промокод.",
    },
    "en": {
        "btn_new": "✨ Create New Presentation",
        "btn_projects": "📂 My Projects",
        "btn_lang": "🌐 Language",
        "btn_balance": "💳 Balance",
        "btn_support": "👨‍💻 Support",
        "btn_admin": "⚙️ Admin",
        "lang_set_confirm": "✅ Interface language set to: <b>English 🇺🇸</b>",
        "bot_brand": "✨ <b>SlideAI KZ</b>",
        "balance_line": "🎫 Balance: <b>{total} presentations</b>",
        "choose_dir": "👇 Choose a category:",
        "ask_topic": "<b>{dir_title}</b>\n\n✍️ Enter the presentation topic:",
        "ask_pres_lang": "<b>{dir_title}</b>\n📌 Topic: <b>«{topic}»</b>\n\n🌐 Choose presentation language:",
        "ask_slides": "<b>{dir_title}</b>\n📌 Topic: <b>«{topic}»</b>\n🌐 Language: {pres_lang}\n\n📄 How many slides?",
        "ask_photo": "<b>{dir_title}</b>\n📌 Topic: <b>«{topic}»</b>\n🌐 Language: {pres_lang} • 📄 {count} slides\n\n🖼 <b>With or without photos?</b>\n<i>Generation starts immediately:</i>",
        "btn_no_photo": "🚫 Without photos",
        "btn_with_photo": "🖼 With photos",
        "slide_unit": "slides",
        "slide_word": "slides",
        "btn_back": "⬅️ Back",
        "progress_preparing": "⏳ <b>Preparing «{topic}»...</b>\n\n<code>[▓▓▓▓▓▓▓▓▓░]</code> <b>95%</b>\n📦 Uploading ready files (.PDF + .PPTX)...\n\n📄 {count} slides • 🎨 {theme}",
        "pdf_caption": "📱 <b>Mobile viewing version (.PDF)</b>",
        "pptx_caption": (
            "📊 <b>Main presentation (.PPTX)</b>\n"
            "📌 <b>{topic}</b>\n"
            "📄 {count} slides • {photo_badge}\n"
            "🎨 {theme}"
        ),
        "photo_badge_none": "🚫 Without photos",
        "photo_badge_with": "🖼 With photos",
        "btn_change_design": "🎨 Change Design",
        "projects_empty": "📂 <b>No saved projects yet.</b>\n\nTap «✨ Create New Presentation» to get started!",
        "projects_header": "📂 <b>My Saved Projects ({total}):</b>\n\n👇 Tap any project to resend <b>.PDF + .PPTX</b>:",
        "balance_screen": (
            "💳 <b>Balance: {total} presentations</b>\n\n"
            "💎 Price: <b>1 presentation — {price} ₸</b> (With / Without photos)\n"
            "🧾 Pay via Kaspi Pay (send PDF receipt) or ⭐️ <b>Telegram Stars ({stars} ⭐️)</b>:"
        ),
        "btn_kaspi_pay": "🔴 Kaspi Pay ({price} ₸)",
        "btn_stars_pay": "⭐️ Telegram Stars ({stars} ⭐️)",
        "stars_title": "1 презентация (SlideAI KZ)",
        "stars_desc": "1 презентация генерациясы (Фотосыз / Фотомен)",
        "stars_success": "⭐️ <b>Telegram Stars төлемі сәтті өтті!</b>\n➕ Балансыңызға <b>+1 презентация</b> қосылды!",
        "kaspi_success": "✅ <b>+{credits} презентация қосылды!</b>\n🎫 Жалпы баланс: <b>{total} презентация</b>",
        "kaspi_error": "❌ <b>Қате: чек қабылданбады.</b>\nСұрақ туындаса, әкімшіге жазыңыз:",
        "btn_promo": "🎟 Promo Code",
        "promo_prompt": "🎟 Enter your promo or gift code:\n<i>Cancel: /cancel</i>",
        "support_screen": (
            "👨‍💻 <b>Support</b>\n\n"
            "If you have any questions about promo codes or payments, message us anytime!\n\n"
            "📱 Direct contact: @{admin_user}\n"
            "🆔 Telegram ID: <code>{user_id}</code>"
        ),
        "btn_direct_admin": "📲 Message Admin Directly",
        "btn_bot_admin": "💬 Message Admin via Bot",
        "support_prompt": "✍️ Type your question or message for the administrator:\n<i>Cancel: /cancel</i>",
        "support_sent": "✅ Your message has been delivered to the administrator! The reply will arrive here.",
        "topic_too_short": "⚠️ Please enter a longer topic.",
        "not_enough_credits": "⚠️ Out of presentation credits. Top up in «💳 Balance» or enter a promo code.",
    },
}


def t(key: str, ui_lang: str = "kk", **kwargs: Any) -> str:
    l = norm_lang(ui_lang)
    tmpl = TEXTS.get(l, TEXTS["kk"]).get(key, TEXTS["kk"].get(key, key))
    if kwargs:
        try:
            return tmpl.format(**kwargs)
        except Exception:
            return tmpl
    return tmpl
