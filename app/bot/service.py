"""
Presentation generation service & Admin Analytics Chart Renderer (Commercial Pro v2 Edition).
Supports:
- Cost-Optimized AI Routing (Free users: DeepSeek -> Fallback; Paid users: DeepSeek -> Gemini -> OpenAI -> Fallback)
- 7-Day & 30-Day Revenue & User Growth Chart Generator (Pillow PNG)
- 360° User History Card formatter (Registration date, Total paid KZT, Generated projects with delete buttons, Complaints count)
- Simultaneous .PPTX + .PDF + .DOCX Defense Speech generation
"""
import io
import re
import time
import logging
from typing import Optional, Tuple, Dict, Any, List

from PIL import Image, ImageDraw

from app.core.types import TelegramSession, PresentationData
from app.core.themes import detect_best_theme_for_topic, THEMES_REGISTRY
from app.core.db import (
    init_db,
    log_user,
    log_generation,
    get_admin_stats,
    get_cached_presentation,
    save_cached_presentation,
    save_user_project,
    get_user_projects,
    get_user_project_by_id,
    list_all_promo_codes,
    has_user_paid,
    get_user_full_history,
    get_time_series_stats,
    get_dynamic_tariffs,
    get_user_persona_style,
    get_cohort_analysis_stats,
    get_flagged_users,
)
from app.core.monitoring import inc_metric, observe_generation_latency, get_prometheus_metrics_snapshot
from app.core.doc_parser import (
    extract_text_from_uploaded_file,
    generate_speaker_defense_text,
    build_defense_speech_docx,
)
from app.core.image_search import populate_presentation_images
from app.ai.client import AIClient
from app.pptx_generator.engine import build_pptx_deck
from app.pptx_generator.pdf_engine import build_pdf_deck, _load_font
from app.bot.session import save_session
import config

logger = logging.getLogger(__name__)

# Ensure DB tables exist
init_db()

ai_client = AIClient(
    deepseek_api_key=config.DEEPSEEK_API_KEY,
    gemini_api_key=config.GEMINI_API_KEY,
    openai_api_key=config.OPENAI_API_KEY,
)


def parse_user_input(text: str) -> Tuple[str, Optional[int], Optional[str]]:
    clean_text = text.strip()
    extracted_count = None
    extracted_theme_id = None

    inline_match = re.search(r"[, -]*(\d{1,2})\s*(беттік|бет|слайдтан|слайд|страниц|slides)\b", clean_text, re.IGNORECASE)
    if inline_match:
        try:
            num = int(inline_match.group(1))
            if config.MIN_SLIDE_COUNT <= num <= config.MAX_SLIDE_COUNT:
                extracted_count = num
                stripped = re.sub(
                    r"[, -]*\d{1,2}\s*(беттік|бет|слайдтан|слайд|страниц|slides)\b", "", clean_text, flags=re.IGNORECASE
                ).strip()
                if len(stripped) >= 2:
                    clean_text = stripped
        except Exception:
            pass

    lower_text = clean_text.lower()
    for theme_id, theme in THEMES_REGISTRY.items():
        if theme.name.lower() in lower_text or theme.nameKz.lower() in lower_text:
            extracted_theme_id = theme_id
            break

    return clean_text, extracted_count, extracted_theme_id


async def generate_deck_for_session(
    session: TelegramSession,
    user_id: Optional[int] = None,
    slide_count: Optional[int] = None,
) -> Tuple[bytes, str, PresentationData, bool]:
    topic = session.pendingTopic or (
        session.lastPresentation.topic if session.lastPresentation else "Жасанды интеллект"
    )
    count = slide_count or session.slideCount or config.DEFAULT_SLIDE_COUNT
    count = max(config.MIN_SLIDE_COUNT, min(count, config.MAX_SLIDE_COUNT))
    language = session.language or "қазақша"
    template_id = session.templateId or "standard"
    with_photos = bool(session.withPhotos)
    image_source = session.imageSource or "ddg"
    paid_flag = has_user_paid(user_id) if user_id else False

    selected_theme = (
        THEMES_REGISTRY[session.designId]
        if session.designId != "auto" and session.designId in THEMES_REGISTRY
        else detect_best_theme_for_topic(topic, with_photos=with_photos)
    )

    t_start = time.time()
    inc_metric("generations_total", 1)
    inc_metric("active_generations", 1)

    persona_style = getattr(session, "personaStyle", None) or (get_user_persona_style(user_id) if user_id else "academic_universal")
    is_storybook = bool(getattr(session, "isStorybook", False) or template_id == "storybook")
    child_name = getattr(session, "childName", None)
    child_avatar_desc = getattr(session, "childAvatarDesc", None)
    if is_storybook:
        with_photos = True
        template_id = "storybook"
        persona_style = "kids_fairy"

    doc_text = session.pendingDocumentText
    from_cache = False
    cache_tmpl_key = f"{template_id}:{persona_style}:{child_name or ''}:{(child_avatar_desc or '')[:32]}" if (is_storybook or persona_style != "academic_universal") else template_id

    try:
        cached_pres = get_cached_presentation(
            topic, count, doc_text=doc_text, language=language, template_id=cache_tmpl_key
        )
        if cached_pres and len(cached_pres.slides) == count:
            logger.info(
                f"⚡ Smart Cache HIT for topic='{topic}' ({count} slides, lang={language})! Applying design='{selected_theme.id}'."
            )
            presentation = cached_pres
            presentation.design_id = selected_theme.id
            presentation.language = language
            presentation.template_id = template_id
            presentation.persona_style = persona_style
            presentation.is_storybook = is_storybook
            presentation.child_name = child_name
            presentation.child_avatar_desc = child_avatar_desc
            from_cache = True
        else:
            presentation = await ai_client.generate_presentation(
                topic=topic,
                slide_count=count,
                design_id=selected_theme.id,
                language=language,
                document_text=doc_text,
                template_id=template_id,
                with_photos=with_photos,
                is_paid_user=paid_flag,
                user_id=user_id,
                persona_style=persona_style,
                is_storybook=is_storybook,
                child_name=child_name,
                child_avatar_desc=child_avatar_desc,
            )
            presentation.design_id = selected_theme.id
            presentation.persona_style = persona_style
            presentation.is_storybook = is_storybook
            presentation.child_name = child_name
            presentation.child_avatar_desc = child_avatar_desc

        if with_photos:
            await populate_presentation_images(presentation, image_source=image_source, user_id=user_id)
            try:
                # Save presentation WITH populated images into Redis + SQLite cache (100 users -> 1 generation!)
                save_cached_presentation(
                    topic, count, presentation, doc_text=doc_text, language=language, template_id=cache_tmpl_key
                )
            except Exception as e:
                logger.warning(f"Failed to update presentation cache with images: {e}")
        else:
            if not from_cache:
                try:
                    save_cached_presentation(
                        topic, count, presentation, doc_text=doc_text, language=language, template_id=cache_tmpl_key
                    )
                except Exception as e:
                    logger.warning(f"Failed to save to presentation cache: {e}")
            presentation.with_photos = False
            presentation.image_source = "none"
            for s_item in presentation.slides:
                s_item.image_bytes_b64 = None
    finally:
        inc_metric("active_generations", -1)
        observe_generation_latency(time.time() - t_start)

    pptx_bytes = build_pptx_deck(presentation)
    base_name = re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", topic)[:40].strip("_") or "presentation"
    clean_filename = f"{base_name}.pptx"

    session.lastPresentation = presentation
    session.pendingTopic = topic
    session.pendingDocumentText = None

    if user_id:
        try:
            save_session(user_id, session)
            save_user_project(user_id, presentation)
            log_generation(
                user_id, topic, count, selected_theme.id, "pptx",
                from_cache=from_cache, with_photos=with_photos,
                image_source=image_source if with_photos else "none",
                language=language, template_id=template_id,
            )
        except Exception as e:
            logger.warning(f"Failed to log/save user project: {e}")

    return pptx_bytes, clean_filename, presentation, from_cache


def build_pdf_for_session(
    session: TelegramSession,
    pptx_bytes: Optional[bytes] = None,
) -> Optional[Tuple[bytes, str]]:
    if not session.lastPresentation:
        return None

    pdf_bytes = build_pdf_deck(session.lastPresentation, pptx_bytes=pptx_bytes)
    base_name = (
        re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", session.lastPresentation.topic)[:40].strip("_")
        or "presentation"
    )
    filename = f"{base_name}.pdf"
    return pdf_bytes, filename


def build_speech_for_session(
    session: TelegramSession,
) -> Optional[Tuple[str, bytes, str]]:
    if not session.lastPresentation:
        return None

    full_text = generate_speaker_defense_text(session.lastPresentation)
    docx_bytes = build_defense_speech_docx(session.lastPresentation)
    base_name = (
        re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", session.lastPresentation.topic)[:35].strip("_")
        or "presentation"
    )
    filename = f"Қорғау_сөзі_{base_name}.docx"
    return full_text, docx_bytes, filename


def reexport_deck_with_theme(
    session: TelegramSession,
    theme_id: str,
    user_id: Optional[int] = None,
) -> Optional[Tuple[bytes, str, str]]:
    if not session.lastPresentation:
        return None

    new_theme = (
        THEMES_REGISTRY[theme_id]
        if theme_id != "auto" and theme_id in THEMES_REGISTRY
        else detect_best_theme_for_topic(session.lastPresentation.topic, with_photos=session.lastPresentation.with_photos)
    )

    session.lastPresentation.design_id = new_theme.id
    pptx_bytes = build_pptx_deck(session.lastPresentation)
    base_name = (
        re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", session.lastPresentation.topic)[:40].strip("_")
        or "presentation"
    )
    clean_filename = f"{base_name}.pptx"

    if user_id:
        try:
            save_session(user_id, session)
            save_user_project(user_id, session.lastPresentation)
        except Exception:
            pass

    return pptx_bytes, clean_filename, new_theme.nameKz


def load_saved_project_for_session(
    session: TelegramSession,
    project_id: int,
    user_id: Optional[int] = None,
) -> Optional[Tuple[bytes, str, PresentationData, str]]:
    pres = get_user_project_by_id(project_id, user_id=user_id)
    if not pres:
        return None

    theme_obj = THEMES_REGISTRY.get(pres.design_id, THEMES_REGISTRY["swiss_minimalism"])
    session.lastPresentation = pres
    session.pendingTopic = pres.topic
    session.slideCount = pres.slide_count
    session.designId = pres.design_id

    if user_id:
        try:
            save_session(user_id, session)
        except Exception:
            pass

    pptx_bytes = build_pptx_deck(pres)
    base_name = re.sub(r"[^a-zA-Z0-9\u0400-\u04FF]", "_", pres.topic)[:40].strip("_") or "presentation"
    filename = f"{base_name}.pptx"
    return pptx_bytes, filename, pres, theme_obj.nameKz


def render_admin_analytics_chart_png(days: int = 7) -> Tuple[bytes, str]:
    """
    Renders a crisp 1200x700 dual-panel PNG analytics chart for /admin (7-day or 30-day):
    - Top Panel: Daily Revenue (₸) bar chart
    - Bottom Panel: Daily New Users & Presentations Generated
    """
    ts = get_time_series_stats(days=days)
    dates = ts["dates"]
    revs = ts["revenues"]
    users = ts["new_users"]
    gens = ts["generations"]

    W, H = 1200, 700
    img = Image.new("RGB", (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)

    f_title = _load_font(26, bold=True)
    f_sub = _load_font(17, bold=True)
    f_lbl = _load_font(13, bold=False)

    draw.text((48, 28), f"AI PRESENTATION BOT — {days} КҮНДІК ДИНАМИКА ГРАФИГІ", font=f_title, fill=(248, 250, 252))
    tot_rev = sum(revs)
    tot_u = sum(users)
    tot_g = sum(gens)
    draw.text(
        (48, 66),
        f"Жалпы табыс: {tot_rev:,} ₸   |   Жаңа қолданушылар: {tot_u} адам   |   Презентациялар: {tot_g} дана",
        font=f_sub,
        fill=(56, 189, 248),
    )

    # Panel 1: Revenue (y: 110 .. 365)
    p1_x0, p1_y0, p1_x1, p1_y1 = 48, 115, W - 48, 365
    draw.rounded_rectangle([p1_x0, p1_y0, p1_x1, p1_y1], radius=12, fill=(30, 41, 59), outline=(51, 65, 85), width=2)
    draw.text((p1_x0 + 20, p1_y0 + 14), f"Күнделікті Табыс (₸) — Соңғы {days} күн", font=f_sub, fill=(16, 185, 129))

    n = max(1, len(dates))
    chart_w = (p1_x1 - p1_x0) - 60
    slot_w = chart_w / n
    bar_w = max(8, int(slot_w * 0.55))
    max_rev = max(max(revs) if revs else 0, 1000)

    for i, (d_str, val) in enumerate(zip(dates, revs)):
        bx = int(p1_x0 + 30 + i * slot_w + (slot_w - bar_w) / 2)
        bh = int((val / max_rev) * 150) if val > 0 else 4
        by = p1_y1 - 36 - bh
        color = (16, 185, 129) if val > 0 else (71, 85, 105)
        draw.rounded_rectangle([bx, by, bx + bar_w, p1_y1 - 36], radius=4, fill=color)
        if n <= 10 or i % 3 == 0 or i == n - 1:
            short_d = d_str[5:]  # MM-DD
            draw.text((bx - 4, p1_y1 - 28), short_d, font=f_lbl, fill=(148, 163, 184))
        if val > 0 and (n <= 10 or i == n - 1):
            draw.text((bx - 6, max(p1_y0 + 42, by - 18)), f"{val}", font=f_lbl, fill=(248, 250, 252))

    # Panel 2: Users & Generations (y: 390 .. 655)
    p2_x0, p2_y0, p2_x1, p2_y1 = 48, 395, W - 48, 655
    draw.rounded_rectangle([p2_x0, p2_y0, p2_x1, p2_y1], radius=12, fill=(30, 41, 59), outline=(51, 65, 85), width=2)
    draw.text(
        (p2_x0 + 20, p2_y0 + 14),
        "Жаңа Қолданушылар (көк) және Жасалған Презентациялар (сары)",
        font=f_sub,
        fill=(96, 165, 250),
    )

    max_ug = max(max(users + gens) if (users or gens) else 0, 5)
    half_bw = max(4, bar_w // 2)
    for i, (d_str, u_val, g_val) in enumerate(zip(dates, users, gens)):
        bx = int(p2_x0 + 30 + i * slot_w + (slot_w - bar_w) / 2)
        uh = int((u_val / max_ug) * 155) if u_val > 0 else 3
        gh = int((g_val / max_ug) * 155) if g_val > 0 else 3
        draw.rectangle([bx, p2_y1 - 36 - uh, bx + half_bw - 1, p2_y1 - 36], fill=(56, 189, 248))
        draw.rectangle([bx + half_bw + 1, p2_y1 - 36 - gh, bx + 2 * half_bw, p2_y1 - 36], fill=(250, 204, 21))
        if n <= 10 or i % 3 == 0 or i == n - 1:
            draw.text((bx - 4, p2_y1 - 28), d_str[5:], font=f_lbl, fill=(148, 163, 184))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    caption = (
        f"📊 <b>Соңғы {days} күндік өсу динамикасы</b>\n"
        f"💰 Табыс: <b>{tot_rev:,} ₸</b> | 👥 Жаңа қолданушылар: <b>{tot_u}</b> | 📑 Презентация: <b>{tot_g}</b>\n\n"
        + "\n".join(ts["alerts"])
    )
    return buf.getvalue(), caption


def format_user_admin_card(user_id_or_profile: Any) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Formats the 360° User History Card for Admin:
    - Қашан тіркелді, соңғы белсенділігі
    - Қанша төледі (₸) және төлем саны
    - 3-себеттік балансы (Бонус / Фотосыз / Фото DDG / OpenAI)
    - Қандай тақырыптар жасады (жобалар тізімі + өшіру батырмалары үшін)
    - Қанша рет шағымданды / хат жазды
    """
    uid = user_id_or_profile["user_id"] if isinstance(user_id_or_profile, dict) else int(user_id_or_profile)
    hist = get_user_full_history(uid)
    prof = hist["profile"]
    b = hist["credits_breakdown"]
    projects = hist["projects"]

    uname = f"@{prof['username']}" if prof.get("username") else "Жоқ"
    fname = prof.get("first_name") or "Белгісіз"
    reg_date = str(prof.get("created_at") or "—")[:16]
    last_act = str(prof.get("last_active") or "—")[:16]

    proj_lines = ""
    for p in projects[:6]:
        proj_lines += f"  • <code>#{p['id']}</code> «{p['topic'][:30]}» ({p['slide_count']} бет)\n"
    if not proj_lines:
        proj_lines = "  (Әзірге жоба жасамаған)\n"

    text = (
        f"👤 <b>360° ҚОЛДАНУШЫ ТАРИХЫ (КАРТОЧКА)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{uid}</code> | 📛 <b>{fname}</b> ({uname})\n"
        f"📅 Тіркелген уақыты: <code>{reg_date}</code> (Соңғы: <code>{last_act}</code>)\n"
        f"💳 Жалпы төлеген сомасы: <b>{hist['total_paid_kzt']:,} ₸</b> ({hist['payments_count']} төлем)\n"
        f"📩 Шағымдар / Хабарламалар саны: <b>{hist['complaints_count']} рет</b>\n\n"
        f"🎫 <b>Баланс (Барлығы: {b['total']} през):</b>\n"
        f"  • 🎁 Бонус: <b>{b['bonus']}</b> | 📄 Фотосыз: <b>{b['no_photo']}</b>\n"
        f"  • 🖼 Фото (DDG): <b>{b['ddg_photo']}</b> | ✨ OpenAI: <b>{b['openai_photo']}</b>\n\n"
        f"👥 <b>Реферал:</b> {prof.get('invited_count', 0)} дос • Сауда: {prof.get('referral_sales_kzt', 0):,} ₸ • Баланс: {prof.get('partner_balance_kzt', 0):,} ₸\n\n"
        f"📂 <b>Жасаған жобалары ({len(projects)}):</b>\n"
        f"{proj_lines}\n"
        f"👇 Төмендегі батырмалармен баланс қосуға, хат жазуға немесе кез келген жобасын өшіруге болады:"
    )
    return text, projects


def format_admin_dashboard_text() -> Tuple[str, int, int]:
    """
    Formats comprehensive admin statistics including Logical Alerts, AI Cost Tracker, Funnel & Promo Codes.
    Returns (text, pending_withdrawals_count, pending_payments_count).
    """
    stats = get_admin_stats()
    tariffs = get_dynamic_tariffs()

    alerts_str = "\n".join(stats.get("logical_alerts", []))

    pkg_lines = ""
    for p in stats.get("packages_breakdown", []):
        t_obj = tariffs.get(p["tariff_id"], config.TARIFF_PLANS.get(p["tariff_id"], {}))
        t_title = t_obj.get("title", p["tariff_id"])
        pkg_lines += f"  • {t_title}: <b>{p['cnt']} дана</b> ({p['sum_kzt']:,} ₸)\n"
    if not pkg_lines:
        pkg_lines = "  (Әзірге сатылым жоқ)\n"

    funnel = stats.get("funnel", {})
    f_start = max(1, funnel.get("start", 0))
    f_topic = funnel.get("topic_entered", 0)
    f_gen = funnel.get("generation_completed", 0)
    f_tar = funnel.get("tariff_viewed", 0)
    f_pay = funnel.get("payment_completed", 0)

    funnel_block = (
        f"  1. Start: <b>{funnel.get('start', 0)}</b> (100%) → Тақырып: <b>{f_topic}</b> ({int(f_topic * 100 / f_start)}%)\n"
        f"  2. Генерация: <b>{f_gen}</b> ({int(f_gen * 100 / f_start)}%) → Тариф: <b>{f_tar}</b> ({int(f_tar * 100 / f_start)}%) → Төлем: <b>{f_pay}</b> ({int(f_pay * 100 / f_start)}%)\n"
    )

    ai_c = stats.get("ai_costs", {})
    ai_line = (
        f"• Бүгін: <b>${ai_c.get('today_usd', 0):.4f} (~{ai_c.get('today_kzt', 0)} ₸)</b> | "
        f"Барлығы: <b>${ai_c.get('total_usd', 0):.4f} (~{ai_c.get('total_kzt', 0)} ₸)</b>"
    )

    promos = list_all_promo_codes()
    promo_str = ", ".join(f"<code>{pr['code']}</code> ({pr['used_count']})" for pr in promos[:5])

    pend_w_cnt = stats.get("pending_withdrawals_count", 0)
    pend_w_kzt = stats.get("pending_withdrawals_kzt", 0)
    pend_p_cnt = stats.get("pending_payments_count", 0)

    text = (
        "📊 <b>AI PRESENTATION BOT PRO v2 — АДМИН ПАНЕЛЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{alerts_str}\n\n"
        "💰 <b>Қаржы және Сатылым:</b>\n"
        f"• Бүгінгі табыс: <b>{stats['revenue_today_kzt']:,} ₸</b> ({stats['payments_today_count']} төлем)\n"
        f"• Жалпы табыс: <b>{stats['revenue_total_kzt']:,} ₸</b> ({stats['payments_total_count']} төлем)\n"
        f"• Қолмен тексеруді күтіп тұрған чектер: <b>{pend_p_cnt} дана</b>\n\n"
        "📈 <b>AI Шығындарын Бақылау (DeepSeek / OpenAI):</b>\n"
        f"{ai_line}\n\n"
        "📊 <b>Воронка (Funnel Аналитика):</b>\n"
        f"{funnel_block}\n"
        "📦 <b>Сатылған пакеттер:</b>\n"
        f"{pkg_lines}\n"
        "👥 <b>Қолданушылар & Генерациялар:</b>\n"
        f"• Тіркелгендер: <b>{stats['total_users']}</b> (Бүгін: {stats['users_today']})\n"
        f"• Презентациялар: <b>{stats['total_generations']}</b> (🖼 Фотомен: {stats.get('photo_generations', 0)} • ⚡ Кэштен: {stats['cached_generations']})\n"
        f"• Выплата сұраныстары: <b>{pend_w_cnt} дана ({pend_w_kzt:,} ₸)</b>\n"
        f"• Промокодтар: {promo_str}\n\n"
        f"⚡ <b>Prometheus & Кэш Метрикалары:</b>\n"
        f"• Latency (Орт / p95): <b>{get_prometheus_metrics_snapshot()['latency_avg_sec']}s / {get_prometheus_metrics_snapshot()['latency_p95_sec']}s</b> | Сурет кэші: <b>{get_prometheus_metrics_snapshot()['image_cache_hits_total']} hit</b>\n"
        f"• 🛡 Анти-фрод Flag-тар: <b>{len(get_flagged_users(50))}</b> | 🤖 Churn тәуекелі (7к): <b>{get_cohort_analysis_stats()['churn_risk_7d_count']}</b> | 💝 Win-back (30к): <b>{get_cohort_analysis_stats()['inactive_30d_count']}</b>"
    )
    return text, pend_w_cnt, pend_p_cnt
