"""
Inline keyboards for 1-tap UX, slide counts, 30 design themes,
PPTX/PDF export, Speaker Defense Speech, Saved User Projects,
Dynamic Kaspi Pay Tariffs, Partner Withdrawal Flow, and Admin Control Center.
"""
import math
import urllib.parse
from typing import Dict, Any, List, Optional
import config
from app.core.types import TelegramSession
from app.core.themes import THEMES_REGISTRY, THEMES_LIST, get_selected_theme_label
from app.core.db import get_dynamic_tariffs, get_kaspi_pay_url


def build_topic_ready_text(session: TelegramSession, user_credits: Optional[int] = None) -> str:
    topic = session.pendingTopic or "Жасанды интеллект"
    theme_label = get_selected_theme_label(session.designId, topic)
    doc_badge = "\n📎 <i>Құжат мәтіні негізінде дайындалады</i>" if session.pendingDocumentText else ""
    cred_line = f"\n🎫 Балансыңызда: <b>{user_credits} презентация</b>" if user_credits is not None else ""
    return (
        f"📌 Тақырып: «{topic}»\n"
        f"🎨 Дизайн: {theme_label}{doc_badge}{cred_line}\n\n"
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


def build_user_projects_keyboard(
    projects: List[Dict[str, Any]], page: int, total_count: int, page_size: int = 6
) -> Dict[str, Any]:
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


def build_tariffs_keyboard() -> Dict[str, Any]:
    """Reads live tariff prices from DB settings."""
    tariffs = get_dynamic_tariffs()
    t_single = tariffs["single"]
    t_hit = tariffs["hit"]
    t_vip = tariffs["vip"]

    return {
        "inline_keyboard": [
            [
                {
                    "text": f"💳 {t_single['title']} — {t_single['price_kzt']:,} ₸ ({t_single['credits']} презентация)",
                    "callback_data": "buy_tariff:single",
                }
            ],
            [
                {
                    "text": f"🔥 {t_hit['title']} — {t_hit['price_kzt']:,} ₸ ({t_hit['credits']} презентация)",
                    "callback_data": "buy_tariff:hit",
                }
            ],
            [
                {
                    "text": f"👑 {t_vip['title']} — {t_vip['price_kzt']:,} ₸ ({t_vip['credits']} презентация)",
                    "callback_data": "buy_tariff:vip",
                }
            ],
            [
                {
                    "text": "👥 Дос шақырып тегін алу (+2 000 ₸ табыс)",
                    "callback_data": "open_referral",
                }
            ],
        ]
    }


def build_payment_instruction_keyboard(tariff_id: str) -> Dict[str, Any]:
    """Shows ONLY the Kaspi Pay Link button (no phone transfer)."""
    tariffs = get_dynamic_tariffs()
    t = tariffs.get(tariff_id, tariffs["hit"])
    pay_url = get_kaspi_pay_url()

    rows: List[List[Dict[str, str]]] = []
    if pay_url and pay_url.startswith("http"):
        rows.append([{"text": f"🔴 Kaspi Pay арқылы төлеу ({t['price_kzt']:,} ₸)", "url": pay_url}])

    rows.append([{"text": "⬅️ Тарифтерге оралу", "callback_data": "open_tariffs"}])
    return {"inline_keyboard": rows}


def build_admin_payment_review_keyboard(payment_id: int, credits: int, amount_kzt: int) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"✅ Растау (+{credits} през • {amount_kzt} ₸)",
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
        "🔥 Санаулы секундта дайын презентация (.PPTX + .PDF) және Қорғау сөзін (Шпаргалка) "
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


def build_admin_keyboard(pending_withdrawals_count: int = 0) -> Dict[str, Any]:
    """Enhanced Admin Control Center with Kaspi Pay Settings & Dynamic Tariff Price Editor."""
    w_badge = f" ({pending_withdrawals_count})" if pending_withdrawals_count > 0 else ""
    return {
        "inline_keyboard": [
            [
                {"text": "🏢 Kaspi Pay & Чек баптау", "callback_data": "admin_kaspi_settings"},
                {"text": "💰 Бағаларды өзгерту", "callback_data": "admin_edit_prices"},
            ],
            [
                {"text": f"💸 Шығару сұраныстары{w_badge}", "callback_data": "admin_withdrawals"},
                {"text": "🧾 Соңғы чектер", "callback_data": "admin_payments"},
            ],
            [
                {"text": "🔍 Қолданушы іздеу / Баланс", "callback_data": "admin_find_user"},
                {"text": "📢 Хабарлама тарату", "callback_data": "admin_broadcast"},
            ],
            [
                {"text": "🔄 Статистиканы жаңарту", "callback_data": "admin_refresh"},
            ],
        ]
    }


def build_admin_kaspi_settings_keyboard() -> Dict[str, Any]:
    """Buttons for Admin to change Kaspi Pay link or reset company to learn from next PDF receipt."""
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
    """Buttons allowing Admin to edit any tariff price and presentation count directly in the bot."""
    tariffs = get_dynamic_tariffs()
    t1 = tariffs["single"]
    t2 = tariffs["hit"]
    t3 = tariffs["vip"]
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"✏️ {t1['title']}: {t1['price_kzt']:,} ₸ ({t1['credits']} през)",
                    "callback_data": "edit_tariff:single",
                }
            ],
            [
                {
                    "text": f"✏️ {t2['title']}: {t2['price_kzt']:,} ₸ ({t2['credits']} през)",
                    "callback_data": "edit_tariff:hit",
                }
            ],
            [
                {
                    "text": f"✏️ {t3['title']}: {t3['price_kzt']:,} ₸ ({t3['credits']} през)",
                    "callback_data": "edit_tariff:vip",
                }
            ],
            [
                {"text": "⬅️ Админ панельге оралу", "callback_data": "admin_refresh"},
            ],
        ]
    }


def build_admin_user_manage_keyboard(target_user_id: int) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "➕ +1 през", "callback_data": f"adm_cred:{target_user_id}:1"},
                {"text": "🔥 +15 (Хит)", "callback_data": f"adm_cred:{target_user_id}:15"},
                {"text": "👑 +40 (VIP)", "callback_data": f"adm_cred:{target_user_id}:40"},
            ],
            [
                {"text": "➖ -1 през", "callback_data": f"adm_cred:{target_user_id}:-1"},
                {"text": "💬 Хат жазу", "callback_data": f"reply_user:{target_user_id}"},
            ],
            [
                {"text": "⬅️ Админ панельге оралу", "callback_data": "admin_refresh"},
            ],
        ]
    }


def build_support_contact_keyboard() -> Dict[str, Any]:
    rows: List[List[Dict[str, str]]] = []
    if config.ADMIN_CONTACT:
        clean_adm = config.ADMIN_CONTACT.lstrip("@").replace("https://t.me/", "").strip()
        if clean_adm:
            rows.append([{"text": f"📲 Тікелей админге жазу (@{clean_adm})", "url": f"https://t.me/{clean_adm}"}])
    rows.append([{"text": "✍️ Бот арқылы админге хабарлама жіберу", "callback_data": "start_support_msg"}])
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
