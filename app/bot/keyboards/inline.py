"""
Inline keyboards for AI Presentation Bot (Commercial Pro v2 Edition):
- 3-Bucket Credit display & DDG Photo Warning disclaimer
- 8 Specialized Academic/Business Templates (including GOST 7.32-2017)
- Dynamic Tariff Packages (with Admin Add / Edit / Delete package controls)
- Full Admin Control Center: 7d/30d Charts, Paginated & Filtered Users, 360° User Card with Project Deletion,
  Promo Code & Bonus Campaign Manager, Segmented Broadcast, AI Cost Tracker, Manual Receipt Approval & CSV/Excel DB Export.
"""
import math
import urllib.parse
from typing import Dict, Any, List, Optional
import config
from app.bot.i18n import t as i18n_t, norm_lang, DIRECTIONS, get_dir_button
from app.core.types import TelegramSession
from app.core.themes import THEMES_REGISTRY, THEMES_LIST, get_selected_theme_label
from app.core.db import get_dynamic_tariffs, get_kaspi_pay_url, get_user_credit_breakdown, get_enabled_generation_modes, get_referat_bot_url, get_presentation_price_kzt, get_stars_price_xtr


def ensure_session_valid_mode(session: TelegramSession) -> Dict[str, bool]:
    """Ensures session photo mode is enabled; if disabled by Admin, switches to an active mode."""
    modes = get_enabled_generation_modes()
    cur_mode = ("gpt-image-2" if session.imageSource == "gpt-image-2" else "ddg") if session.withPhotos else "none"
    if not modes.get(cur_mode, True):
        if modes.get("none", True):
            session.withPhotos = False
            session.imageSource = "ddg"
        elif modes.get("ddg", True):
            session.withPhotos = True
            session.imageSource = "ddg"
        elif modes.get("gpt-image-2", True):
            session.withPhotos = True
            session.imageSource = "gpt-image-2"
    return modes


def build_topic_ready_text(
    session: TelegramSession,
    user_id: Optional[int] = None,
    user_credits: Optional[int] = None,
) -> str:
    ensure_session_valid_mode(session)
    topic = session.pendingTopic or "Жасанды интеллект"
    theme_label = get_selected_theme_label(session.designId, topic, with_photos=session.withPhotos)
    lang_info = config.SUPPORTED_LANGUAGES.get(session.language, config.SUPPORTED_LANGUAGES["қазақша"])
    tmpl_info = config.TEMPLATE_LIBRARY.get(session.templateId, config.TEMPLATE_LIBRARY["standard"])
    p_style = config.PERSONA_STYLES.get(getattr(session, "personaStyle", "academic_universal"), config.PERSONA_STYLES["academic_universal"])

    warning_block = ""
    if session.withPhotos:
        if session.imageSource == "gpt-image-2":
            photo_line = "✨ Фото режимі: <b>OpenAI gpt-image-2 (AI генерация • VIP/Pro/500₸)</b>"
        else:
            photo_line = "🖼 Фото режимі: <b>Қосулы (Интернеттен мысал фото • ВАУ дизайн)</b>"
            warning_block = f"\n\n{config.DDG_PHOTO_WARNING_TEXT}"
    else:
        photo_line = "🚫 Фото режимі: <b>Фотосыз (Минимализм • Тегін бонус / 200₸)</b>"

    doc_badge = "\n📎 <i>Құжат мәтіні негізінде дайындалады</i>" if session.pendingDocumentText else ""
    cred_line = ""
    if user_id is not None:
        b = get_user_credit_breakdown(user_id)
        cred_line = (
            f"\n🎫 <b>Сіздің лимиттеріңіз (Жалпы: {b['total']}):</b>\n"
            f"   • 🎁 Бонус (Фотосыз / Фото): <b>{b['bonus']}</b> | 📄 Фотосыз: <b>{b['no_photo']}</b>\n"
            f"   • 🖼 Фотомен: <b>{b['ddg_photo']}</b> | ✨ OpenAI (gpt-image-2): <b>{b['openai_photo']}</b>"
        )
    elif user_credits is not None:
        cred_line = f"\n🎫 Баланс: <b>{user_credits} презентация</b>"

    return (
        f"📌 Тақырып: «{topic}»\n"
        f"🎨 Дизайн: {theme_label}\n"
        f"📐 Құрылым: {tmpl_info['title']} • 🌐 Тіл: {lang_info['label']}\n"
        f"🎭 Стиль: <b>{p_style['title']}</b>" + (f" • 👶 Кейіпкер: <b>{session.childName}</b>" if getattr(session, "childName", None) else "") + "\n"
        f"{photo_line}{doc_badge}{cred_line}{warning_block}\n\n"
        f"📦 Дайын болғанда бірден <b>3 файл (.PPTX + .PDF + .DOCX Қорғау сөзі)</b> жіберіледі!\n"
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

    modes = ensure_session_valid_mode(session)
    no_photo_active = not session.withPhotos
    ddg_active = session.withPhotos and session.imageSource == "ddg"
    gpt_active = session.withPhotos and session.imageSource == "gpt-image-2"

    row_photo: List[Dict[str, str]] = []
    if modes.get("none", True):
        row_photo.append({
            "text": "✅ 🚫 Фотосыз" if no_photo_active else "🚫 Фотосыз",
            "callback_data": "set_photo:none",
        })
    if modes.get("ddg", True):
        row_photo.append({
            "text": "✅ 🖼 Фото" if ddg_active else "🖼 Фото",
            "callback_data": "set_photo:ddg",
        })
    if modes.get("gpt-image-2", True):
        row_photo.append({
            "text": "✅ ✨ OpenAI Фото" if gpt_active else "✨ OpenAI Фото",
            "callback_data": "set_photo:gpt-image-2",
        })

    row_lang = []
    for l_code, l_meta in config.SUPPORTED_LANGUAGES.items():
        is_sel = session.language == l_code
        row_lang.append({
            "text": f"✅ {l_meta['short']}" if is_sel else l_meta["short"],
            "callback_data": f"set_lang:{l_code}",
        })

    theme_label = get_selected_theme_label(session.designId, session.pendingTopic, with_photos=session.withPhotos)
    tmpl_info = config.TEMPLATE_LIBRARY.get(session.templateId, config.TEMPLATE_LIBRARY["standard"])
    p_style = config.PERSONA_STYLES.get(getattr(session, "personaStyle", "academic_universal"), config.PERSONA_STYLES["academic_universal"])

    return {
        "inline_keyboard": [
            [
                {
                    "text": f"🚀 Бірден жасау ({session.slideCount} бет • PPTX+PDF+DOCX)",
                    "callback_data": f"gen_now:{session.slideCount}",
                }
            ],
            row_counts_1,
            row_counts_2,
            row_photo,
            row_lang,
            [
                {
                    "text": f"📐 {tmpl_info['title'][:18]}",
                    "callback_data": "open_templates:topic",
                },
                {
                    "text": f"🎨 Дизайн ({theme_label[:14]})",
                    "callback_data": "open_themes:0:topic",
                },
            ],
            [
                {
                    "text": f"🎭 {config.PERSONA_STYLES.get(getattr(session, 'personaStyle', 'academic_universal'), config.PERSONA_STYLES['academic_universal'])['short']}",
                    "callback_data": "open_persona:topic",
                },
                {
                    "text": "🧚 Ертегі (Бала атымен)",
                    "callback_data": "start_storybook",
                },
            ],
        ]
    }


def build_templates_keyboard(session: TelegramSession, mode: str = "default") -> Dict[str, Any]:
    rows: List[List[Dict[str, str]]] = []
    for t_id, t_info in config.TEMPLATE_LIBRARY.items():
        prefix = "✅ " if session.templateId == t_id else ""
        rows.append([
            {
                "text": f"{prefix}{t_info['title']}",
                "callback_data": f"pick_template:{t_id}:{mode}",
            }
        ])
    if mode == "topic" and session.pendingTopic:
        rows.append([{"text": "⬅️ Тақырыпқа оралу", "callback_data": "back_to_topic"}])
    return {"inline_keyboard": rows}


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


def build_post_generation_keyboard(has_pdf: bool = False, ui_lang: str = "kk") -> Dict[str, Any]:
    l = norm_lang(ui_lang)
    rows: List[List[Dict[str, str]]] = [
        [
            {"text": i18n_t("btn_change_design", l), "callback_data": "open_themes:0:reexport"},
            {"text": i18n_t("btn_projects", l), "callback_data": "open_projects:0"},
        ],
        [{"text": i18n_t("btn_new", l), "callback_data": "new_presentation"}],
    ]
    return {"inline_keyboard": rows}


def build_persona_styles_keyboard(session: TelegramSession, mode: str = "default") -> Dict[str, Any]:
    rows: List[List[Dict[str, str]]] = []
    cur = getattr(session, "personaStyle", "academic_universal")
    for p_id, p_info in config.PERSONA_STYLES.items():
        prefix = "✅ " if cur == p_id else ""
        rows.append([
            {
                "text": f"{prefix}{p_info['title']}",
                "callback_data": f"pick_persona:{p_id}:{mode}",
            }
        ])
    if mode == "topic" and session.pendingTopic:
        rows.append([{"text": "⬅️ Тақырыпқа оралу", "callback_data": "back_to_topic"}])
    return {"inline_keyboard": rows}


def build_user_projects_keyboard(
    projects: List[Dict[str, Any]], page: int, total_count: int, page_size: int = 6, ui_lang: str = "kk"
) -> Dict[str, Any]:
    l = norm_lang(ui_lang)
    unit = i18n_t("slide_unit", l)
    rows: List[List[Dict[str, str]]] = []
    for proj in projects:
        proj_id = proj["id"]
        topic = proj["topic"][:34]
        slides = proj["slide_count"]
        label = f"📄 {topic} ({slides} {unit})"
        rows.append([{"text": label, "callback_data": f"load_proj:{proj_id}"}])

    total_pages = max(1, math.ceil(total_count / page_size))
    if total_pages > 1:
        safe_page = ((page % total_pages) + total_pages) % total_pages
        rows.append(
            [
                {"text": "⬅️", "callback_data": f"open_projects:{safe_page - 1}"},
                {"text": f"{safe_page + 1} / {total_pages}", "callback_data": "noop"},
                {"text": "➡️", "callback_data": f"open_projects:{safe_page + 1}"},
            ]
        )

    rows.append([{"text": i18n_t("btn_new", l), "callback_data": "new_presentation"}])
    return {"inline_keyboard": rows}


def build_tariffs_keyboard(user_id: Optional[int] = None) -> Dict[str, Any]:
    """Reads all active tariff packages (including custom Admin packages, excluding deleted ones)."""
    tariffs = get_dynamic_tariffs(user_id=user_id)
    icons = {
        "single": "💳",
        "single_photo": "🖼",
        "single_openai": "✨",
        "hit": "🔥",
        "pro": "🚀",
        "vip": "👑",
    }
    rows: List[List[Dict[str, str]]] = []
    for k, t in tariffs.items():
        ic = icons.get(k, "📦")
        np_c = int(t.get("no_photo_credits", 0))
        ddg_c = int(t.get("ddg_photo_credits", 0))
        oai_c = int(t.get("openai_photo_credits", 0))
        if t["credits"] == 1:
            sub = "OpenAI фото" if oai_c else ("Фотомен" if ddg_c else "Фотосыз")
        else:
            sub = f"{t['credits']} през ({np_c}/{ddg_c}/{oai_c})"
        rows.append([
            {
                "text": f"{ic} {t['title']} — {t['price_kzt']:,} ₸ ({sub})",
                "callback_data": f"buy_tariff:{k}",
            }
        ])

    rows.append([
        {
            "text": "🎟 Промокод / Науқан кодын енгізу",
            "callback_data": "enter_promo",
        }
    ])
    rows.append([
        {
            "text": "👥 Дос шақырып тегін алу (+2 000 ₸ табыс)",
            "callback_data": "open_referral",
        }
    ])
    return {"inline_keyboard": rows}


def build_payment_instruction_keyboard(tariff_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    tariffs = get_dynamic_tariffs(user_id=user_id)
    t = tariffs.get(tariff_id, next(iter(tariffs.values())) if tariffs else {"price_kzt": 200})
    pay_url = get_kaspi_pay_url()

    rows: List[List[Dict[str, str]]] = []
    if pay_url and pay_url.startswith("http"):
        rows.append([{"text": f"🔴 Kaspi Pay арқылы төлеу ({t['price_kzt']:,} ₸)", "url": pay_url}])

    rows.append([{"text": "🎟 Промокод енгізу (1 реттік)", "callback_data": "enter_promo"}])
    rows.append([{"text": "⬅️ Тарифтерге оралу", "callback_data": "open_tariffs"}])
    return {"inline_keyboard": rows}


def build_admin_payment_review_keyboard(payment_id: int, credits: int, amount_kzt: int) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"✅ Қолмен растау (+{credits} през • {amount_kzt} ₸)",
                    "callback_data": f"approve_pay:{payment_id}",
                },
                {
                    "text": "❌ Қабылдамау",
                    "callback_data": f"reject_pay:{payment_id}",
                },
            ]
        ]
    }


def build_referral_keyboard(ref_link: str, partner_balance_kzt: int = 0) -> Dict[str, Any]:
    share_text = (
        "🔥 Санаулы секундта сапалы дайын презентация (.PPTX + .PDF + .DOCX Қорғау сөзі) "
        "жасап беретін күшті AI бот! Кірсең 1 презентация ТЕГІН беріледі 👇"
    )
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_text)}"
    withdraw_label = (
        f"💸 Табысты шығару (Қолжетімді: {partner_balance_kzt} ₸)"
        if partner_balance_kzt >= config.MIN_WITHDRAWAL_KZT
        else f"💸 Табысты шығару (Мин. {config.MIN_WITHDRAWAL_KZT} ₸)"
    )
    rows: List[List[Dict[str, str]]] = [
        [{"text": "📤 Достарға сілтемені жіберу", "url": share_url}],
        [{"text": withdraw_label, "callback_data": "withdraw_partner"}],
        [{"text": "💳 Тарифтерді көру", "callback_data": "open_tariffs"}],
    ]
    return {"inline_keyboard": rows}


def build_admin_withdrawal_action_keyboard(withdrawal_id: int, amount_kzt: int) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"✅ Төленді ({amount_kzt} ₸)",
                    "callback_data": f"pay_withdraw:{withdrawal_id}",
                },
                {
                    "text": "❌ Бас тарту",
                    "callback_data": f"reject_withdraw:{withdrawal_id}",
                },
            ]
        ]
    }


def build_admin_keyboard(pending_withdrawals_count: int = 0, pending_payments_count: int = 0) -> Dict[str, Any]:
    """Clean Modern Admin Control Center (SlideAI KZ)."""
    w_badge = f" ({pending_withdrawals_count})" if pending_withdrawals_count > 0 else ""
    p_badge = f" ({pending_payments_count})" if pending_payments_count > 0 else ""
    return {
        "inline_keyboard": [
            [
                {"text": "📊 График (7 күн)", "callback_data": "admin_charts:7"},
                {"text": "📈 График (30 күн)", "callback_data": "admin_charts:30"},
            ],
            [
                {"text": "👥 Қолданушылар", "callback_data": "admin_users:0:all"},
                {"text": "🔍 Іздеу (ID / @tag)", "callback_data": "admin_find_user"},
            ],
            [
                {"text": "💰 Бағалар (₸ / ⭐️ Stars)", "callback_data": "admin_edit_prices"},
                {"text": "🎛 2 Режим (Фото/Фотосыз)", "callback_data": "admin_gen_modes"},
            ],
            [
                {"text": "🎟 Промокодтар", "callback_data": "admin_promos"},
                {"text": "📢 Хабарлама тарату", "callback_data": "admin_broadcast_menu"},
            ],
            [
                {"text": f"🧾 Чектер{p_badge}", "callback_data": "admin_payments"},
                {"text": f"💸 Выплаталар{w_badge}", "callback_data": "admin_withdrawals"},
            ],
            [
                {"text": "📈 AI шығындары", "callback_data": "admin_ai_costs"},
                {"text": "🛡 Анти-фрод", "callback_data": "admin_antifraud"},
            ],
            [
                {"text": "📊 Когорта / Churn", "callback_data": "admin_cohorts_churn"},
                {"text": "⚡ Метрикалар", "callback_data": "admin_prometheus"},
            ],
            [
                {"text": "💾 База (CSV/Excel)", "callback_data": "admin_export_db"},
                {"text": "🏢 Kaspi Pay баптау", "callback_data": "admin_kaspi_settings"},
            ],
            [
                {"text": "🔄 Статистиканы жаңарту", "callback_data": "admin_refresh"},
            ],
        ]
    }


def build_admin_users_list_keyboard(
    users: List[Dict[str, Any]],
    page: int,
    total_count: int,
    filter_mode: str = "all",
    page_size: int = 8,
) -> Dict[str, Any]:
    rows: List[List[Dict[str, str]]] = [
        [
            {"text": "✅ Барлығы" if filter_mode == "all" else "Барлығы", "callback_data": "admin_users:0:all"},
            {"text": "✅ 🖼 Фотомен" if filter_mode == "photo" else "🖼 Фотомен", "callback_data": "admin_users:0:photo"},
            {"text": "✅ 💎 VIP/Төлеген" if filter_mode == "paid" else "💎 VIP/Төлеген", "callback_data": "admin_users:0:paid"},
            {"text": "✅ 🔥 Белсенді" if filter_mode == "active" else "🔥 Белсенді", "callback_data": "admin_users:0:active"},
        ]
    ]

    for u in users:
        uid = u["user_id"]
        uname = f"@{u['username']}" if u.get("username") else (u.get("first_name") or str(uid))
        paid_ic = "💎" if u.get("has_paid") else "👤"
        rows.append([
            {
                "text": f"{paid_ic} {uname[:22]} (ID: {uid} • {u.get('credits', 0)} през)",
                "callback_data": f"adm_view_user:{uid}",
            }
        ])

    total_pages = max(1, math.ceil(total_count / page_size))
    safe_page = ((page % total_pages) + total_pages) % total_pages
    if total_pages > 1:
        rows.append([
            {"text": "⬅️ Алдыңғы", "callback_data": f"admin_users:{safe_page - 1}:{filter_mode}"},
            {"text": f"{safe_page + 1} / {total_pages}", "callback_data": "noop"},
            {"text": "Келесі ➡️", "callback_data": f"admin_users:{safe_page + 1}:{filter_mode}"},
        ])

    rows.append([{"text": "⬅️ Админ панельге оралу", "callback_data": "admin_refresh"}])
    return {"inline_keyboard": rows}


def build_admin_promos_keyboard(promos: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows: List[List[Dict[str, str]]] = [
        [
            {"text": "➕ Жаңа Промокод / Науқан қосу", "callback_data": "adm_add_promo"},
        ]
    ]
    for pr in promos[:12]:
        code = pr["code"]
        disc = int(pr.get("discount_percent") or 0)
        bon = int(pr.get("bonus_credits") or 0)
        used = int(pr.get("used_count") or 0)
        badge = f"+{bon} през" if bon > 0 and disc == 0 else f"-{disc}%"
        rows.append([
            {"text": f"🎟 {code} ({badge} • {used} рет)", "callback_data": "noop"},
            {"text": "🗑 Өшіру", "callback_data": f"adm_del_promo:{code}"},
        ])
    rows.append([{"text": "⬅️ Админ панельге оралу", "callback_data": "admin_refresh"}])
    return {"inline_keyboard": rows}


def build_admin_broadcast_segment_keyboard() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": "👥 Барлық қолданушыларға", "callback_data": "adm_bcast_seg:all"}],
            [{"text": "💎 Тек VIP / Pro (Төлем жасағандарға)", "callback_data": "adm_bcast_seg:vip_paid"}],
            [{"text": "🖼 Тек Фотомен презентация жасағандарға", "callback_data": "adm_bcast_seg:photo_users"}],
            [{"text": "🔥 Тек Белсенділерге (Соңғы 7 күн)", "callback_data": "adm_bcast_seg:active_7d"}],
            [{"text": "⬅️ Админ панельге оралу", "callback_data": "admin_refresh"}],
        ]
    }


def build_admin_kaspi_settings_keyboard() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "🔗 Kaspi Pay сілтемесін өзгерту", "callback_data": "admin_set_pay_url"},
            ],
            [
                {"text": "🔄 Компанияны жаңа чекпен орнату (/reset)", "callback_data": "admin_reset_seller"},
            ],
            [
                {"text": "⬅️ Админ панельге оралу", "callback_data": "admin_refresh"},
            ],
        ]
    }


def build_admin_price_editor_keyboard() -> Dict[str, Any]:
    """Allows Admin to edit unified 1-presentation price (KZT) & Telegram Stars price (XTR)."""
    price_kzt = get_presentation_price_kzt()
    stars_xtr = get_stars_price_xtr()
    rows: List[List[Dict[str, str]]] = [
        [{"text": f"💰 1 презентация бағасы: {price_kzt:,} ₸ (Өзгерту)", "callback_data": "adm_set_pres_price"}],
        [{"text": f"⭐️ Telegram Stars бағасы: {stars_xtr} ⭐️ (Өзгерту)", "callback_data": "adm_set_stars_price"}],
        [{"text": "🎛 2 Режимді қосу/өшіру (Фотосыз / Фотомен)", "callback_data": "admin_gen_modes"}],
        [{"text": "⬅️ Админ панель", "callback_data": "admin_refresh"}],
    ]
    return {"inline_keyboard": rows}


def build_admin_gen_modes_keyboard() -> Dict[str, Any]:
    """Allows Admin to toggle the 2 presentation generation modes (Фотосыз / Фотомен)."""
    modes = get_enabled_generation_modes()
    m_none = modes.get("none", True)
    m_ddg = modes.get("ddg", True)

    st_none = "🟢 ҚОСУЛЫ" if m_none else "🔴 ӨШІРУЛІ"
    st_ddg = "🟢 ҚОСУЛЫ" if m_ddg else "🔴 ӨШІРУЛІ"

    rows: List[List[Dict[str, str]]] = [
        [{"text": f"{st_none} • 🚫 Фотосыз", "callback_data": "adm_toggle_mode:none"}],
        [{"text": f"{st_ddg} • 🖼 Фотомен", "callback_data": "adm_toggle_mode:ddg"}],
        [
            {"text": "📄 Тек «Фотосыз»", "callback_data": "adm_mode_preset:only_nophoto"},
            {"text": "🔄 Екеуін де қосу", "callback_data": "adm_mode_preset:all_on"},
        ],
        [
            {"text": "💰 Тарифтерге өту", "callback_data": "admin_edit_prices"},
            {"text": "⬅️ Админ панель", "callback_data": "admin_refresh"},
        ],
    ]
    return {"inline_keyboard": rows}


def build_admin_user_manage_keyboard(target_user_id: int, projects: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    rows: List[List[Dict[str, str]]] = [
        [
            {"text": "🎁 +1", "callback_data": f"adm_cred:{target_user_id}:1"},
            {"text": "💎 +5", "callback_data": f"adm_cred:{target_user_id}:5"},
            {"text": "🔥 +10", "callback_data": f"adm_cred:{target_user_id}:10"},
            {"text": "➖ -1", "callback_data": f"adm_cred:{target_user_id}:-1"},
        ],
        [
            {"text": "💬 Жауап жазу", "callback_data": f"reply_user:{target_user_id}"},
        ],
    ]

    if projects:
        for pr in projects[:5]:
            rows.append([
                {
                    "text": f"🗑 Өшіру: #{pr['id']} «{pr['topic'][:22]}»",
                    "callback_data": f"adm_del_proj:{pr['id']}:{target_user_id}",
                }
            ])

    rows.append([
        {"text": "👥 Тізім", "callback_data": "admin_users:0:all"},
        {"text": "⬅️ Админ панель", "callback_data": "admin_refresh"},
    ])
    return {"inline_keyboard": rows}


def build_balance_keyboard(ui_lang: str = "kk") -> Dict[str, Any]:
    l = norm_lang(ui_lang)
    pay_url = get_kaspi_pay_url()
    rows: List[List[Dict[str, str]]] = []
    pay_row: List[Dict[str, str]] = []
    price_kzt = get_presentation_price_kzt()
    stars_xtr = get_stars_price_xtr()
    if pay_url and pay_url.startswith("http"):
        pay_row.append({"text": i18n_t("btn_kaspi_pay", l, price=price_kzt), "url": pay_url})
    pay_row.append({"text": i18n_t("btn_stars_pay", l, stars=stars_xtr), "callback_data": "pay_stars:1"})
    rows.append(pay_row)
    rows.append([{"text": i18n_t("btn_promo", l), "callback_data": "enter_promo"}])
    return {"inline_keyboard": rows}


def build_support_contact_keyboard(ui_lang: str = "kk") -> Dict[str, Any]:
    l = norm_lang(ui_lang)
    clean_adm = (config.ADMIN_CONTACT or "dev_d1darbek").lstrip("@").replace("https://t.me/", "").strip()
    rows: List[List[Dict[str, str]]] = [
        [{"text": i18n_t("btn_direct_admin", l), "url": f"https://t.me/{clean_adm}"}],
        [{"text": i18n_t("btn_bot_admin", l), "callback_data": "start_support_msg"}],
    ]
    return {"inline_keyboard": rows}


def build_admin_support_inbox_keyboard(users: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows: List[List[Dict[str, str]]] = []
    for u in users:
        uid = u["user_id"]
        uname = u.get("username")
        label = f"💬 @{uname}" if uname else f"💬 {u.get('first_name') or f'user_{uid}'}"
        rows.append([{"text": label, "callback_data": f"adm_support_view:{uid}"}])
    return {"inline_keyboard": rows}


def build_admin_reply_user_keyboard(user_id: int) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "💬 Жауап жазу", "callback_data": f"reply_user:{user_id}"},
                {"text": "👤 Профилін ашу", "callback_data": f"adm_view_user:{user_id}"},
            ]
        ]
    }


# ============================================================================
# TRILINGUAL STEP-BY-STEP WIZARD KEYBOARDS (kk / ru / en) — Minimal Modern UI
# ============================================================================

def build_ui_language_keyboard() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": "🇰🇿 Қазақша", "callback_data": "set_ui_lang:kk"}],
            [{"text": "🇷🇺 Русский (Орысша)", "callback_data": "set_ui_lang:ru"}],
            [{"text": "🇺🇸 English (Ағылшынша)", "callback_data": "set_ui_lang:en"}],
        ]
    }


def build_direction_selection_keyboard(ui_lang: str = "kk") -> Dict[str, Any]:
    l = norm_lang(ui_lang)
    dir_ids = [
        "standard",
        "scientific",
        "diploma",
        "business",
        "lesson",
        "medical",
        "law",
        "marketing",
        "ecology",
    ]
    rows: List[List[Dict[str, str]]] = []
    # Clean 2-column grid for modern minimal look
    for i in range(0, len(dir_ids), 2):
        pair = dir_ids[i : i + 2]
        rows.append([
            {"text": get_dir_button(d_id, l), "callback_data": f"select_dir:{d_id}"}
            for d_id in pair
        ])
    return {"inline_keyboard": rows}


def build_wiz_academic_lang_keyboard(ui_lang: str = "kk") -> Dict[str, Any]:
    l = norm_lang(ui_lang)
    return {
        "inline_keyboard": [
            [{"text": "🇰🇿 Қазақша", "callback_data": "wiz_acad_lang:қазақша"}],
            [{"text": "🇷🇺 Русский (Орысша)", "callback_data": "wiz_acad_lang:русский"}],
            [{"text": "🇺🇸 English (Ағылшынша)", "callback_data": "wiz_acad_lang:english"}],
            [{"text": i18n_t("btn_back", l), "callback_data": "new_presentation"}],
        ]
    }


def build_wiz_academic_slides_keyboard(ui_lang: str = "kk") -> Dict[str, Any]:
    l = norm_lang(ui_lang)
    unit = i18n_t("slide_unit", l)
    return {
        "inline_keyboard": [
            [
                {"text": f"📄 8 {unit}", "callback_data": "wiz_acad_slides:8"},
                {"text": f"📄 10 {unit}", "callback_data": "wiz_acad_slides:10"},
                {"text": f"📄 12 {unit}", "callback_data": "wiz_acad_slides:12"},
            ],
            [
                {"text": f"📄 15 {unit}", "callback_data": "wiz_acad_slides:15"},
                {"text": f"📄 20 {unit}", "callback_data": "wiz_acad_slides:20"},
                {"text": f"📄 25 {unit}", "callback_data": "wiz_acad_slides:25"},
            ],
            [{"text": i18n_t("btn_back", l), "callback_data": "new_presentation"}],
        ]
    }


def build_wiz_academic_photo_keyboard(ui_lang: str = "kk") -> Dict[str, Any]:
    l = norm_lang(ui_lang)
    modes = get_enabled_generation_modes()
    row_modes: List[Dict[str, str]] = []
    if modes.get("none", True):
        row_modes.append({"text": i18n_t("btn_no_photo", l), "callback_data": "wiz_acad_gen:none"})
    if modes.get("ddg", True) or modes.get("gpt-image-2", True):
        row_modes.append({"text": i18n_t("btn_with_photo", l), "callback_data": "wiz_acad_gen:photo"})
    if not row_modes:
        row_modes.append({"text": i18n_t("btn_no_photo", l), "callback_data": "wiz_acad_gen:none"})
    return {
        "inline_keyboard": [
            row_modes,
            [{"text": i18n_t("btn_back", l), "callback_data": "new_presentation"}],
        ]
    }
