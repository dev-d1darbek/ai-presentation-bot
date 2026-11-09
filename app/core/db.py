"""
Database Engine for AI Presentation Bot (Commercial Pro v2 Edition):
1. Dual-Backend: SQLite with WAL mode (busy_timeout=10000) + PostgreSQL (DATABASE_URL) support
2. 3-Bucket Credit System:
   - bonus_credits: Тегін бонус (тек «Бір реттік» фотосыз және «Бір реттік + ФОТО» DDG үшін!)
   - no_photo_credits: Фотосыз презентациялар
   - ddg_photo_credits: Интернеттен/ЖИ мысал фотомен презентациялар
   - openai_photo_credits: OpenAI gpt-image-2 фотомен презентациялар (тек VIP/Pro/Хит/500₸)
3. Dynamic Admin Tariff Package CRUD (Жаңа пакет қосу, баға мен лимиттерді өзгерту, пакетті өшіру)
4. One-Time Per User Promo Codes & Bonus Campaigns ('promo_usages' table + Add/Delete/Stats)
5. AI Cost Tracking ('ai_usage_logs' table: DeepSeek, Gemini, OpenAI Text, gpt-image-2, DDG, Fallback)
6. 7-Day & 30-Day Time-Series Analytics + Logical Alerts ("🚨 Бүгін табыс 50% төмендеді!")
7. Paginated & Filtered Users ('all', 'photo', 'paid', 'active'), 360° User History Card, Project Deletion, Manual Receipt Approval & CSV/Excel Export
"""
import base64
import copy
import csv
import datetime as dt
import hashlib
import io
import json
import logging
import os
import re
import sqlite3
import threading
import zipfile
from typing import Dict, Any, List, Optional, Tuple

import httpx

import config
from app.core.types import PresentationData
from app.core.redis_cache import redis_get, redis_set

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "bot.db")


def serialize_presentation(presentation: PresentationData) -> str:
    if hasattr(presentation, "model_dump"):
        return json.dumps(presentation.model_dump(), ensure_ascii=False)
    return json.dumps(presentation.dict(), ensure_ascii=False)


def deserialize_presentation(raw_json: str) -> PresentationData:
    data = json.loads(raw_json)
    if hasattr(PresentationData, "model_validate"):
        return PresentationData.model_validate(data)
    return PresentationData.parse_obj(data)


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
    except Exception:
        pass
    return conn


def normalize_topic_key(topic: str) -> str:
    clean = topic.lower().strip()
    clean = re.sub(r"[^\w\s\u0400-\u04FF]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def compute_doc_hash(doc_text: Optional[str]) -> str:
    if not doc_text or not doc_text.strip():
        return ""
    return hashlib.sha256(doc_text.strip().encode("utf-8", errors="ignore")).hexdigest()[:16]


def init_db():
    """Initializes all tables, columns, indexes, and built-in promo codes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS receipts (
        receipt_no TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        company_bin TEXT,
        used_at TEXT NOT NULL
    )
    """)

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        credits INTEGER DEFAULT {config.WELCOME_FREE_CREDITS},
        bonus_credits INTEGER DEFAULT {config.WELCOME_FREE_CREDITS},
        no_photo_credits INTEGER DEFAULT 0,
        ddg_photo_credits INTEGER DEFAULT 0,
        openai_photo_credits INTEGER DEFAULT 0,
        photo_credits INTEGER DEFAULT 0,
        has_paid INTEGER DEFAULT 0,
        active_promo_code TEXT DEFAULT NULL,
        streak_days INTEGER DEFAULT 1,
        last_streak_date TEXT DEFAULT NULL,
        referred_by INTEGER DEFAULT NULL,
        invited_count INTEGER DEFAULT 0,
        referral_sales_kzt INTEGER DEFAULT 0,
        partner_milestones_paid INTEGER DEFAULT 0,
        partner_balance_kzt INTEGER DEFAULT 0,
        partner_total_earned_kzt INTEGER DEFAULT 0,
        complaints_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    user_migrations = [
        f"ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT {config.WELCOME_FREE_CREDITS}",
        f"ALTER TABLE users ADD COLUMN bonus_credits INTEGER DEFAULT {config.WELCOME_FREE_CREDITS}",
        "ALTER TABLE users ADD COLUMN no_photo_credits INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN ddg_photo_credits INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN openai_photo_credits INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN photo_credits INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN has_paid INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN active_promo_code TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN streak_days INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN last_streak_date TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN invited_count INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN referral_sales_kzt INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN partner_milestones_paid INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN partner_balance_kzt INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN partner_total_earned_kzt INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN complaints_count INTEGER DEFAULT 0",
    ]
    for mig in user_migrations:
        try:
            cursor.execute(mig)
        except Exception:
            pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        tariff_id TEXT,
        amount_kzt INTEGER,
        credits_added INTEGER,
        no_photo_added INTEGER DEFAULT 0,
        ddg_photo_added INTEGER DEFAULT 0,
        openai_photo_added INTEGER DEFAULT 0,
        photo_credits_added INTEGER DEFAULT 0,
        promo_code TEXT DEFAULT NULL,
        receipt_hash TEXT,
        receipt_number TEXT UNIQUE,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP DEFAULT NULL
    )
    """)

    for pay_mig in (
        "ALTER TABLE payments ADD COLUMN no_photo_added INTEGER DEFAULT 0",
        "ALTER TABLE payments ADD COLUMN ddg_photo_added INTEGER DEFAULT 0",
        "ALTER TABLE payments ADD COLUMN openai_photo_added INTEGER DEFAULT 0",
        "ALTER TABLE payments ADD COLUMN photo_credits_added INTEGER DEFAULT 0",
        "ALTER TABLE payments ADD COLUMN promo_code TEXT DEFAULT NULL",
    ):
        try:
            cursor.execute(pay_mig)
        except Exception:
            pass

    try:
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_receipt_unique
            ON payments(receipt_number)
            WHERE receipt_number != '' AND receipt_number IS NOT NULL
        """)
    except Exception:
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY,
        discount_percent INTEGER NOT NULL DEFAULT 0,
        bonus_credits INTEGER NOT NULL DEFAULT 0,
        description TEXT,
        max_uses INTEGER DEFAULT 100000,
        used_count INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    try:
        cursor.execute("ALTER TABLE promo_codes ADD COLUMN bonus_credits INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass

    # One-time per user promo usage tracker ("промокодтар тек Бір реттік істесін")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS promo_usages (
        user_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, code)
    )
    """)

    for code_key, p_info in config.DEFAULT_PROMO_CODES.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO promo_codes (code, discount_percent, bonus_credits, description, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (
                code_key.upper(),
                int(p_info.get("discount_percent", 0)),
                int(p_info.get("bonus_credits", 0)),
                p_info["description"],
            ),
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        provider TEXT NOT NULL,
        units INTEGER DEFAULT 1,
        cost_usd REAL DEFAULT 0.0,
        cost_kzt INTEGER DEFAULT 0,
        topic TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS funnel_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_name TEXT NOT NULL,
        props_json TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount_kzt INTEGER,
        requisites TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP DEFAULT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic TEXT,
        slide_count INTEGER,
        design_id TEXT,
        format TEXT DEFAULT 'pptx',
        from_cache INTEGER DEFAULT 0,
        with_photos INTEGER DEFAULT 0,
        image_source TEXT DEFAULT 'none',
        language TEXT DEFAULT 'қазақша',
        template_id TEXT DEFAULT 'standard',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    for gen_mig in (
        "ALTER TABLE generations ADD COLUMN from_cache INTEGER DEFAULT 0",
        "ALTER TABLE generations ADD COLUMN with_photos INTEGER DEFAULT 0",
        "ALTER TABLE generations ADD COLUMN image_source TEXT DEFAULT 'none'",
        "ALTER TABLE generations ADD COLUMN language TEXT DEFAULT 'қазақша'",
        "ALTER TABLE generations ADD COLUMN template_id TEXT DEFAULT 'standard'",
    ):
        try:
            cursor.execute(gen_mig)
        except Exception:
            pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS presentation_cache (
        cache_key TEXT PRIMARY KEY,
        norm_topic TEXT,
        slide_count INTEGER,
        doc_hash TEXT DEFAULT '',
        presentation_json TEXT,
        hit_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic TEXT,
        slide_count INTEGER,
        design_id TEXT,
        presentation_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# ============================================================================
# AI COST TRACKING (📈 AI ШЫҒЫНДАРЫН БАҚЫЛАУ)
# ============================================================================

def log_ai_usage(user_id: Optional[int], provider: str, units: int = 1, topic: str = ""):
    unit_cost = config.AI_COST_RATES_USD.get(provider, 0.0)
    cost_usd = round(unit_cost * max(1, units), 5)
    cost_kzt = int(round(cost_usd * config.USD_TO_KZT_RATE))
    try:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO ai_usage_logs (user_id, provider, units, cost_usd, cost_kzt, topic)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id or 0, provider, units, cost_usd, cost_kzt, (topic or "")[:80]),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to log AI usage: {e}")


def get_ai_cost_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    rows_all = conn.execute(
        """
        SELECT provider, count(*) as calls, coalesce(sum(units), 0) as total_units,
               coalesce(sum(cost_usd), 0.0) as usd, coalesce(sum(cost_kzt), 0) as kzt
        FROM ai_usage_logs
        GROUP BY provider
        ORDER BY usd DESC
        """
    ).fetchall()

    row_today = conn.execute(
        """
        SELECT coalesce(sum(cost_usd), 0.0) as usd, coalesce(sum(cost_kzt), 0) as kzt, count(*) as calls
        FROM ai_usage_logs
        WHERE date(created_at) = date('now')
        """
    ).fetchone()

    row_total = conn.execute(
        """
        SELECT coalesce(sum(cost_usd), 0.0) as usd, coalesce(sum(cost_kzt), 0) as kzt, count(*) as calls
        FROM ai_usage_logs
        """
    ).fetchone()
    conn.close()

    return {
        "by_provider": [dict(r) for r in rows_all],
        "today_usd": round(float(row_today["usd"] or 0.0), 4),
        "today_kzt": int(row_today["kzt"] or 0),
        "today_calls": int(row_today["calls"] or 0),
        "total_usd": round(float(row_total["usd"] or 0.0), 4),
        "total_kzt": int(row_total["kzt"] or 0),
        "total_calls": int(row_total["calls"] or 0),
    }


# ============================================================================
# FUNNEL ANALYTICS
# ============================================================================

def _send_external_analytics(user_id: int, event_name: str, props: Dict[str, Any]):
    try:
        if config.MIXPANEL_TOKEN:
            payload = {
                "event": event_name,
                "properties": {
                    "token": config.MIXPANEL_TOKEN,
                    "distinct_id": str(user_id),
                    "time": int(dt.datetime.now().timestamp()),
                    **props,
                },
            }
            b64_data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
            with httpx.Client(timeout=3.0) as c:
                c.get(f"https://api.mixpanel.com/track?data={b64_data}")
        if config.POSTHOG_API_KEY:
            ph_payload = {
                "api_key": config.POSTHOG_API_KEY,
                "event": event_name,
                "distinct_id": str(user_id),
                "properties": props,
            }
            with httpx.Client(timeout=3.0) as c:
                c.post(f"{config.POSTHOG_HOST.rstrip('/')}/capture/", json=ph_payload)
    except Exception:
        pass


def track_funnel_event(user_id: int, event_name: str, props: Optional[Dict[str, Any]] = None):
    if not user_id:
        return
    p_dict = props or {}
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO funnel_events (user_id, event_name, props_json) VALUES (?, ?, ?)",
            (user_id, event_name, json.dumps(p_dict, ensure_ascii=False)),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    if config.MIXPANEL_TOKEN or config.POSTHOG_API_KEY:
        threading.Thread(
            target=_send_external_analytics,
            args=(user_id, event_name, p_dict),
            daemon=True,
        ).start()


def get_funnel_stats() -> Dict[str, int]:
    stages = [
        "start",
        "topic_entered",
        "generation_started",
        "generation_completed",
        "tariff_viewed",
        "payment_completed",
    ]
    res = {s: 0 for s in stages}
    try:
        conn = get_db_connection()
        for s in stages:
            row = conn.execute(
                "SELECT count(DISTINCT user_id) as cnt FROM funnel_events WHERE event_name = ?",
                (s,),
            ).fetchone()
            res[s] = int(row["cnt"]) if row else 0
        u_cnt = conn.execute("SELECT count(*) as c FROM users").fetchone()["c"]
        g_cnt = conn.execute("SELECT count(DISTINCT user_id) as c FROM generations").fetchone()["c"]
        p_cnt = conn.execute("SELECT count(DISTINCT user_id) as c FROM payments WHERE status = 'approved'").fetchone()["c"]
        res["start"] = max(res["start"], u_cnt)
        res["generation_completed"] = max(res["generation_completed"], g_cnt)
        res["generation_started"] = max(res["generation_started"], res["generation_completed"])
        res["topic_entered"] = max(res["topic_entered"], res["generation_started"])
        res["payment_completed"] = max(res["payment_completed"], p_cnt)
        conn.close()
    except Exception:
        pass
    return res


# ============================================================================
# ONE-TIME PROMO CODES & BONUS CAMPAIGNS (промокодтар тек Бір реттік істесін)
# ============================================================================

def get_promo_code_info(code: str) -> Optional[Dict[str, Any]]:
    if not code or not code.strip():
        return None
    clean = code.strip().upper()
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM promo_codes WHERE code = ? AND is_active = 1 AND used_count < max_uses",
        (clean,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def has_user_used_promo(user_id: int, code: str) -> bool:
    clean = code.strip().upper()
    conn = get_db_connection()
    row = conn.execute(
        "SELECT 1 FROM promo_usages WHERE user_id = ? AND code = ?",
        (user_id, clean),
    ).fetchone()
    conn.close()
    return row is not None


def create_or_update_promo_code(
    code: str,
    discount_percent: int = 50,
    description: str = "",
    bonus_credits: int = 0,
    max_uses: int = 100000,
) -> Dict[str, Any]:
    clean = code.strip().upper()
    disc = max(0, min(int(discount_percent), 95))
    b_cred = max(0, int(bonus_credits))
    if b_cred > 0 and not description:
        desc = f"{clean} — +{b_cred} тегін презентация (Науқан)"
    else:
        desc = description.strip() or f"{clean} — {disc}% жеңілдік"
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO promo_codes (code, discount_percent, bonus_credits, description, max_uses, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
        ON CONFLICT(code) DO UPDATE SET
            discount_percent = excluded.discount_percent,
            bonus_credits = excluded.bonus_credits,
            description = excluded.description,
            max_uses = excluded.max_uses,
            is_active = 1
        """,
        (clean, disc, b_cred, desc, max_uses),
    )
    conn.commit()
    conn.close()
    return {"code": clean, "discount_percent": disc, "bonus_credits": b_cred, "description": desc}


def delete_promo_code(code: str) -> bool:
    clean = code.strip().upper()
    conn = get_db_connection()
    cur = conn.execute("DELETE FROM promo_codes WHERE code = ?", (clean,))
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def apply_promo_code_to_user(user_id: int, code: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Applies a promo code to a user ONCE ONLY ('промокодтар тек Бір реттік істесін'):
    - If user already used this code in 'promo_usages' -> rejects immediately!
    - If bonus_credits > 0 (Gift/Bonus Campaign): awards bonus_credits immediately and marks used.
    - If discount_percent > 0: activates one-time discount for the user's next tariff purchase and records in promo_usages.
    """
    info = get_promo_code_info(code)
    if not info:
        return False, "❌ Мұндай промокод табылмады немесе белсенді емес.", None

    clean_code = info["code"]
    log_user(user_id)

    if has_user_used_promo(user_id, clean_code):
        return (
            False,
            f"⚠️ <b>«{clean_code}» промокодын сіз бұрын қолданғансыз!</b>\nӘр промокод тек <b>1 рет (бір реттік)</b> қана жұмыс істейді.",
            None,
        )

    conn = get_db_connection()
    conn.execute(
        "INSERT OR IGNORE INTO promo_usages (user_id, code) VALUES (?, ?)",
        (user_id, clean_code),
    )
    conn.execute(
        "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?",
        (clean_code,),
    )

    bonus_c = int(info.get("bonus_credits") or 0)
    disc_pct = int(info.get("discount_percent") or 0)

    if bonus_c > 0 and disc_pct == 0:
        conn.execute(
            "UPDATE users SET credits = credits + ?, bonus_credits = bonus_credits + ? WHERE user_id = ?",
            (bonus_c, bonus_c, user_id),
        )
        conn.commit()
        conn.close()
        return (
            True,
            f"🎁 <b>«{clean_code}» сыйлық науқаны белсендірілді!</b>\n"
            f"➕ Сізге <b>+{bonus_c} тегін презентация</b> («Бір реттік» немесе «Бір реттік + ФОТО» үшін) қосылды!",
            info,
        )

    if bonus_c > 0:
        conn.execute(
            "UPDATE users SET credits = credits + ?, bonus_credits = bonus_credits + ?, active_promo_code = ? WHERE user_id = ?",
            (bonus_c, bonus_c, clean_code, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET active_promo_code = ? WHERE user_id = ?",
            (clean_code, user_id),
        )
    conn.commit()
    conn.close()
    return (
        True,
        f"🎉 <b>«{clean_code}» промокоды белсендірілді (1 реттік)!</b>\n"
        f"🏷 Сізге <b>«Бір реттік» пакеттерге -{disc_pct}% жеңілдік</b> берілді ({info['description']})!",
        info,
    )


def get_user_active_promo(user_id: int) -> Optional[Dict[str, Any]]:
    prof = get_user_profile(user_id)
    code = prof.get("active_promo_code")
    if not code:
        return None
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM promo_codes WHERE code = ?", (code.upper(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def clear_user_active_promo(user_id: int):
    conn = get_db_connection()
    conn.execute("UPDATE users SET active_promo_code = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_discounted_price(base_price: int, discount_percent: int) -> int:
    if discount_percent <= 0:
        return base_price
    return max(50, int(round(base_price * (100 - discount_percent) / 100.0)))


def list_all_promo_codes() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = [dict(r) for r in conn.execute("SELECT * FROM promo_codes ORDER BY code ASC").fetchall()]
    conn.close()
    return rows


# ============================================================================
# DYNAMIC SETTINGS, ADMIN TARIFF PACKAGE CRUD & RECEIPTS
# ============================================================================

def get_setting(key: str) -> Optional[str]:
    conn = get_db_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def set_setting(key: str, value: str):
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def delete_setting(key: str):
    conn = get_db_connection()
    conn.execute("DELETE FROM settings WHERE key = ?", (key,))
    conn.commit()
    conn.close()


def get_seller_setting() -> Optional[Dict[str, Any]]:
    raw = get_setting("seller")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def set_seller_setting(data: Dict[str, Any]):
    set_setting("seller", json.dumps(data, ensure_ascii=False))


def reset_seller_setting():
    delete_setting("seller")


def get_kaspi_pay_url() -> str:
    saved = get_setting("kaspi_pay_url")
    if saved and saved.strip():
        return saved.strip()
    return config.KASPI_PAY_URL


def set_kaspi_pay_url(url: str):
    set_setting("kaspi_pay_url", url.strip())


def get_disabled_tariff_ids() -> set:
    deleted_raw = get_setting("deleted_tariffs")
    if not deleted_raw:
        return set()
    try:
        return set(json.loads(deleted_raw))
    except Exception:
        return set()


def get_enabled_generation_modes() -> Dict[str, bool]:
    """
    Returns which of the 3 presentation generation modes are enabled:
    - 'none': 🚫 Фотосыз («Бір реттік»)
    - 'ddg': 🖼 Фотомен (Интернет/ЖИ)
    - 'gpt-image-2': ✨ OpenAI Фотомен (gpt-image-2)
    """
    default_modes = {"none": True, "ddg": True, "gpt-image-2": True}
    raw = get_setting("enabled_gen_modes")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                for k in default_modes:
                    if k in parsed:
                        default_modes[k] = bool(parsed[k])
        except Exception:
            pass
    if not any(default_modes.values()):
        default_modes["none"] = True
    return default_modes


def set_generation_mode_enabled(mode: str, enabled: bool) -> Dict[str, bool]:
    modes = get_enabled_generation_modes()
    if mode in modes:
        modes[mode] = bool(enabled)
    if not any(modes.values()):
        modes["none"] = True
    set_setting("enabled_gen_modes", json.dumps(modes))
    return modes


def toggle_generation_mode(mode: str) -> Tuple[bool, Dict[str, bool]]:
    modes = get_enabled_generation_modes()
    if mode not in modes:
        return True, modes
    new_val = not modes[mode]
    if not new_val and sum(1 for v in modes.values() if v) <= 1:
        return False, modes
    modes[mode] = new_val
    set_setting("enabled_gen_modes", json.dumps(modes))
    return True, modes


def set_only_nophoto_mode() -> Dict[str, bool]:
    modes = {"none": True, "ddg": False, "gpt-image-2": False}
    set_setting("enabled_gen_modes", json.dumps(modes))
    return modes


def enable_all_generation_modes() -> Dict[str, bool]:
    modes = {"none": True, "ddg": True, "gpt-image-2": True}
    set_setting("enabled_gen_modes", json.dumps(modes))
    return modes


def get_dynamic_tariffs(user_id: Optional[int] = None, include_disabled: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Loads tariff plans (supporting Admin-created custom packages and Admin enable/disable toggles).
    Applies one-time promo discount ONLY to 1-presentation («Бір реттік») packages!
    """
    raw = get_setting("tariffs")
    disabled_ids = get_disabled_tariff_ids()

    base: Dict[str, Dict[str, Any]] = {}
    for k, v in config.TARIFF_PLANS.items():
        if not include_disabled and k in disabled_ids:
            continue
        item = copy.deepcopy(v)
        item["is_enabled"] = (k not in disabled_ids)
        base[k] = item

    if raw:
        try:
            saved = json.loads(raw)
            for k, v in saved.items():
                if k == "teacher":
                    continue
                if not include_disabled and k in disabled_ids:
                    continue
                if isinstance(v, dict):
                    if k in base:
                        base[k].update(v)
                        base[k]["is_enabled"] = (k not in disabled_ids)
                    else:
                        item = copy.deepcopy(v)
                        item["is_enabled"] = (k not in disabled_ids)
                        base[k] = item
        except Exception:
            pass

    if user_id:
        promo = get_user_active_promo(user_id)
        if promo and int(promo.get("discount_percent") or 0) > 0:
            disc = int(promo["discount_percent"])
            for k, t_info in base.items():
                # ЕРЕЖЕ: Промокодтағы 50% жеңілдік ТЕК 1 реттік пакеттерге (credits == 1) ғана жұмыс жасайды!
                is_single_pkg = (int(t_info.get("credits", 1)) == 1) or (k in ("single", "single_photo", "single_openai"))
                if is_single_pkg:
                    orig_p = int(t_info["price_kzt"])
                    t_info["original_price_kzt"] = orig_p
                    t_info["price_kzt"] = get_discounted_price(orig_p, disc)
                    t_info["discount_percent"] = disc
                    t_info["promo_code"] = promo["code"]
    return base


def update_tariff_setting(
    tariff_id: str,
    price_kzt: int,
    credits: Optional[int] = None,
    no_photo_credits: Optional[int] = None,
    ddg_photo_credits: Optional[int] = None,
    openai_photo_credits: Optional[int] = None,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    tariffs = get_dynamic_tariffs(include_disabled=True)
    if tariff_id not in tariffs:
        tariffs[tariff_id] = {
            "id": tariff_id,
            "title": title or f"«{tariff_id.upper()}»",
            "price_kzt": int(price_kzt),
            "credits": int(credits or 10),
            "no_photo_credits": int(no_photo_credits if no_photo_credits is not None else (credits or 10)),
            "ddg_photo_credits": int(ddg_photo_credits or 0),
            "openai_photo_credits": int(openai_photo_credits or 0),
            "with_photos": bool((ddg_photo_credits or 0) > 0 or (openai_photo_credits or 0) > 0),
            "description": "",
        }
    t = tariffs[tariff_id]
    t["price_kzt"] = int(price_kzt)
    if title:
        t["title"] = title
    if no_photo_credits is not None or ddg_photo_credits is not None or openai_photo_credits is not None:
        np_c = int(no_photo_credits if no_photo_credits is not None else t.get("no_photo_credits", 0))
        ddg_c = int(ddg_photo_credits if ddg_photo_credits is not None else t.get("ddg_photo_credits", 0))
        oai_c = int(openai_photo_credits if openai_photo_credits is not None else t.get("openai_photo_credits", 0))
        t["no_photo_credits"] = np_c
        t["ddg_photo_credits"] = ddg_c
        t["openai_photo_credits"] = oai_c
        t["credits"] = np_c + ddg_c + oai_c
        t["with_photos"] = (ddg_c + oai_c) > 0
        t["description"] = f"{t['credits']} презентация ({np_c} фотосыз + {ddg_c} фотомен + {oai_c} OpenAI)"
    elif credits is not None and credits > 0:
        t["credits"] = int(credits)
        if t.get("openai_photo_credits", 0) > 0 and t.get("no_photo_credits", 0) == 0:
            t["openai_photo_credits"] = int(credits)
        elif t.get("ddg_photo_credits", 0) > 0 and t.get("no_photo_credits", 0) == 0:
            t["ddg_photo_credits"] = int(credits)
        else:
            t["no_photo_credits"] = int(credits)

    # Un-delete if it was previously deleted
    deleted_raw = get_setting("deleted_tariffs")
    if deleted_raw:
        deleted_ids = set(json.loads(deleted_raw))
        if tariff_id in deleted_ids:
            deleted_ids.remove(tariff_id)
            set_setting("deleted_tariffs", json.dumps(list(deleted_ids)))

    set_setting("tariffs", json.dumps(tariffs, ensure_ascii=False))
    return t


def create_custom_tariff_package(
    title: str,
    price_kzt: int,
    no_photo_credits: int,
    ddg_photo_credits: int = 0,
    openai_photo_credits: int = 0,
) -> Dict[str, Any]:
    """Allows Admin to create a brand new tariff package inside the bot."""
    slug = re.sub(r"[^a-zA-Z0-9]", "", title.lower())[:12] or f"pkg_{int(dt.datetime.now().timestamp()) % 10000}"
    tariff_id = f"custom_{slug}_{int(dt.datetime.now().timestamp()) % 1000}"
    clean_title = title if title.startswith("«") else f"«{title}»"
    return update_tariff_setting(
        tariff_id=tariff_id,
        price_kzt=price_kzt,
        no_photo_credits=no_photo_credits,
        ddg_photo_credits=ddg_photo_credits,
        openai_photo_credits=openai_photo_credits,
        title=clean_title,
    )


def set_tariff_package_enabled(tariff_id: str, enabled: bool) -> bool:
    """Enables or disables a tariff package without losing its settings so it can be re-enabled anytime."""
    all_tariffs = get_dynamic_tariffs(include_disabled=True)
    if tariff_id not in all_tariffs:
        return False
    disabled_ids = get_disabled_tariff_ids()
    if enabled:
        disabled_ids.discard(tariff_id)
    else:
        disabled_ids.add(tariff_id)
    set_setting("deleted_tariffs", json.dumps(list(disabled_ids)))
    return True


def toggle_tariff_package(tariff_id: str) -> bool:
    """Toggles a tariff package between enabled (True) and disabled (False), returning the new state."""
    disabled_ids = get_disabled_tariff_ids()
    now_enabled = tariff_id in disabled_ids
    set_tariff_package_enabled(tariff_id, now_enabled)
    return now_enabled


def enable_all_tariff_packages() -> None:
    """Re-enables all tariff packages."""
    set_setting("deleted_tariffs", json.dumps([]))


def delete_tariff_package(tariff_id: str) -> bool:
    """Disables/hides a tariff package (can be re-enabled anytime via toggle_tariff_package or update_tariff_setting)."""
    return set_tariff_package_enabled(tariff_id, False)


def receipt_used(rno: str) -> bool:
    if not rno:
        return False
    conn = get_db_connection()
    r1 = conn.execute("SELECT 1 FROM receipts WHERE receipt_no = ?", (rno,)).fetchone()
    r2 = conn.execute(
        "SELECT 1 FROM payments WHERE receipt_number = ? AND status IN ('approved', 'pending')", (rno,)
    ).fetchone()
    conn.close()
    return (r1 is not None) or (r2 is not None)


def save_receipt(uid: int, rno: str, amount: int, bin_: str) -> bool:
    if not rno:
        return False
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO receipts (receipt_no, user_id, amount, company_bin, used_at) VALUES (?, ?, ?, ?, ?)",
            (rno, uid, amount, bin_, dt.datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


# ============================================================================
# USER REGISTRATION, 3-DAY STREAK BONUS, 3-BUCKET CREDITS & REFERRAL SYSTEM
# ============================================================================

def log_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    referrer_id: Optional[int] = None,
    today_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Logs or updates a user, processes referral bonuses, and tracks the 3-day daily login streak.
    Free bonus credits are stored in 'bonus_credits' (usable for 'Бір реттік' фотосыз and 'Бір реттік + ФОТО' DDG, never OpenAI!).
    """
    result = {
        "is_new": False,
        "referrer_id": None,
        "free_slide_awarded": False,
        "referrer_invited_count": 0,
        "partner_reward_kzt": 0,
        "streak_days": 1,
        "streak_bonus_awarded": False,
    }
    if not user_id:
        return result

    today_str = today_override or dt.date.today().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()

    if existing:
        last_date_str = existing["last_streak_date"]
        cur_streak = int(existing["streak_days"] or 1)
        streak_bonus = False

        if last_date_str != today_str:
            try:
                last_d = dt.date.fromisoformat(last_date_str) if last_date_str else None
                cur_d = dt.date.fromisoformat(today_str)
                if last_d and (cur_d - last_d).days == 1:
                    cur_streak += 1
                    if cur_streak % config.STREAK_DAYS_FOR_FREE_SLIDE == 0:
                        streak_bonus = True
                else:
                    cur_streak = 1
            except Exception:
                cur_streak = 1

        bonus_cred = 1 if streak_bonus else 0
        cursor.execute(
            """
            UPDATE users
            SET username = coalesce(?, username),
                first_name = coalesce(?, first_name),
                streak_days = ?,
                last_streak_date = ?,
                credits = credits + ?,
                bonus_credits = bonus_credits + ?,
                last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (username, first_name, cur_streak, today_str, bonus_cred, bonus_cred, user_id),
        )
        conn.commit()
        conn.close()
        result["streak_days"] = cur_streak
        result["streak_bonus_awarded"] = streak_bonus
        return result

    valid_referrer = None
    if referrer_id and referrer_id != user_id:
        cursor.execute(
            "SELECT user_id, invited_count, referral_sales_kzt, partner_milestones_paid FROM users WHERE user_id = ?",
            (referrer_id,),
        )
        ref_row = cursor.fetchone()
        if ref_row:
            valid_referrer = referrer_id

    w_cred = config.WELCOME_FREE_CREDITS
    cursor.execute(
        """
        INSERT INTO users (
            user_id, username, first_name, credits, bonus_credits,
            no_photo_credits, ddg_photo_credits, openai_photo_credits, photo_credits,
            has_paid, streak_days, last_streak_date, referred_by, last_active
        )
        VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 1, ?, ?, CURRENT_TIMESTAMP)
        """,
        (user_id, username, first_name, w_cred, w_cred, today_str, valid_referrer),
    )
    result["is_new"] = True

    if valid_referrer:
        cursor.execute(
            "UPDATE users SET invited_count = invited_count + 1 WHERE user_id = ?",
            (valid_referrer,),
        )
        cursor.execute(
            "SELECT invited_count, referral_sales_kzt, partner_milestones_paid FROM users WHERE user_id = ?",
            (valid_referrer,),
        )
        ref_updated = cursor.fetchone()
        new_inv_count = ref_updated["invited_count"]
        sales_kzt = ref_updated["referral_sales_kzt"]
        milestones_paid = ref_updated["partner_milestones_paid"]

        result["referrer_id"] = valid_referrer
        result["referrer_invited_count"] = new_inv_count

        if new_inv_count > 0 and new_inv_count % config.REFERRAL_FRIENDS_FOR_FREE_SLIDE == 0:
            cursor.execute(
                "UPDATE users SET credits = credits + 1, bonus_credits = bonus_credits + 1 WHERE user_id = ?",
                (valid_referrer,),
            )
            result["free_slide_awarded"] = True

        if new_inv_count >= config.PARTNER_MIN_INVITED_USERS:
            total_milestones = sales_kzt // config.PARTNER_SALES_THRESHOLD_KZT
            unpaid_milestones = total_milestones - milestones_paid
            if unpaid_milestones > 0:
                reward = unpaid_milestones * config.PARTNER_REWARD_KZT
                cursor.execute(
                    """
                    UPDATE users
                    SET partner_milestones_paid = ?,
                        partner_balance_kzt = partner_balance_kzt + ?,
                        partner_total_earned_kzt = partner_total_earned_kzt + ?
                    WHERE user_id = ?
                    """,
                    (total_milestones, reward, reward, valid_referrer),
                )
                result["partner_reward_kzt"] = reward

    conn.commit()
    conn.close()
    return result


def get_user_profile(user_id: int) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)

    try:
        log_user(user_id)
    except Exception as e:
        logger.warning(f"log_user failed for {user_id}: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)

    return {
        "user_id": user_id,
        "username": None,
        "first_name": None,
        "credits": 0,
        "bonus_credits": 0,
        "no_photo_credits": 0,
        "ddg_photo_credits": 0,
        "openai_photo_credits": 0,
        "photo_credits": 0,
        "has_paid": 0,
        "active_promo_code": None,
        "streak_days": 1,
        "last_streak_date": None,
        "referred_by": None,
        "invited_count": 0,
        "referral_sales_kzt": 0,
        "partner_milestones_paid": 0,
        "partner_balance_kzt": 0,
        "partner_total_earned_kzt": 0,
        "complaints_count": 0,
    }


def get_user_credit_breakdown(user_id: int) -> Dict[str, int]:
    """
    Returns detailed 3-bucket + bonus breakdown for a user:
    - bonus: Тегін бонус (жарайды: Фотосыз НЕМЕСЕ Фото DDG)
    - no_photo: Ақылы фотосыз лимит
    - ddg_photo: Ақылы Фото (DDG) лимиті
    - openai_photo: Ақылы OpenAI gpt-image-2 лимиті
    - total: Барлық қолжетімді презентация саны
    """
    p = get_user_profile(user_id)
    bonus = max(0, int(p.get("bonus_credits") or 0))
    no_p = max(0, int(p.get("no_photo_credits") or 0))
    ddg_p = max(0, int(p.get("ddg_photo_credits") or 0))
    oai_p = max(0, int(p.get("openai_photo_credits") or 0))
    total = max(int(p.get("credits") or 0), bonus + no_p + ddg_p + oai_p)
    return {
        "total": total,
        "bonus": bonus,
        "no_photo": no_p,
        "ddg_photo": ddg_p,
        "openai_photo": oai_p,
        "has_paid": int(p.get("has_paid") or 0),
    }


def get_user_credits(user_id: int) -> int:
    return get_user_credit_breakdown(user_id)["total"]


def get_user_photo_credits(user_id: int) -> int:
    b = get_user_credit_breakdown(user_id)
    return b["ddg_photo"] + b["openai_photo"] + b["bonus"]


def get_user_openai_credits(user_id: int) -> int:
    return get_user_credit_breakdown(user_id)["openai_photo"]


def has_user_paid(user_id: int) -> bool:
    if config.is_admin(user_id):
        return True
    b = get_user_credit_breakdown(user_id)
    return bool(b["has_paid"] or b["no_photo"] > 0 or b["ddg_photo"] > 0 or b["openai_photo"] > 0)


def consume_user_credit(user_id: int, with_photos: bool = False, image_source: str = "ddg") -> bool:
    """
    Atomically consumes 1 presentation credit BEFORE AI generation according to exact user rules:
    1. If with_photos=True and image_source=='gpt-image-2' (OpenAI gpt-image-2):
       - ONLY allowed if openai_photo_credits > 0! (Never consumes bonus_credits or ddg_photo_credits).
    2. If with_photos=True and image_source=='ddg' («Бір реттік + ФОТО»):
       - Consumes ddg_photo_credits first, OR bonus_credits (since free bonus allows «Бір реттік + ФОТО» and «Бір реттік»!).
    3. If with_photos=False («Бір реттік» фотосыз):
       - Consumes no_photo_credits first, OR bonus_credits, OR legacy credits.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if with_photos and image_source == "gpt-image-2":
        cursor.execute(
            """
            UPDATE users
            SET openai_photo_credits = openai_photo_credits - 1,
                photo_credits = max(0, photo_credits - 1),
                credits = max(0, credits - 1)
            WHERE user_id = ? AND openai_photo_credits > 0
            """,
            (user_id,),
        )
        ok = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    if with_photos:
        # DDG photo mode: try ddg_photo_credits first, then bonus_credits
        cursor.execute(
            """
            UPDATE users
            SET ddg_photo_credits = ddg_photo_credits - 1,
                photo_credits = max(0, photo_credits - 1),
                credits = max(0, credits - 1)
            WHERE user_id = ? AND ddg_photo_credits > 0
            """,
            (user_id,),
        )
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return True

        cursor.execute(
            """
            UPDATE users
            SET bonus_credits = bonus_credits - 1,
                credits = max(0, credits - 1)
            WHERE user_id = ? AND bonus_credits > 0
            """,
            (user_id,),
        )
        ok = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    # No-photo mode («Бір реттік» фотосыз): try no_photo_credits -> bonus_credits -> general credits
    cursor.execute(
        """
        UPDATE users
        SET no_photo_credits = no_photo_credits - 1,
            credits = max(0, credits - 1)
        WHERE user_id = ? AND no_photo_credits > 0
        """,
        (user_id,),
    )
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return True

    cursor.execute(
        """
        UPDATE users
        SET bonus_credits = bonus_credits - 1,
            credits = max(0, credits - 1)
        WHERE user_id = ? AND bonus_credits > 0
        """,
        (user_id,),
    )
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return True

    cursor.execute(
        "UPDATE users SET credits = credits - 1 WHERE user_id = ? AND credits > 0",
        (user_id,),
    )
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def add_user_credits(
    user_id: int,
    credits_to_add: int,
    no_photo_to_add: Optional[int] = None,
    ddg_photo_to_add: int = 0,
    openai_photo_to_add: int = 0,
    is_bonus: bool = False,
) -> int:
    log_user(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()

    if is_bonus:
        cursor.execute(
            """
            UPDATE users
            SET credits = max(0, credits + ?),
                bonus_credits = max(0, bonus_credits + ?)
            WHERE user_id = ?
            """,
            (credits_to_add, credits_to_add, user_id),
        )
    else:
        if no_photo_to_add is None and ddg_photo_to_add == 0 and openai_photo_to_add == 0:
            if credits_to_add > 0:
                no_photo_to_add = credits_to_add
            else:
                no_photo_to_add = credits_to_add
        np_add = int(no_photo_to_add or 0)
        ddg_add = int(ddg_photo_to_add or 0)
        oai_add = int(openai_photo_to_add or 0)
        tot_add = np_add + ddg_add + oai_add if (np_add or ddg_add or oai_add) else credits_to_add
        cursor.execute(
            """
            UPDATE users
            SET credits = max(0, credits + ?),
                no_photo_credits = max(0, no_photo_credits + ?),
                ddg_photo_credits = max(0, ddg_photo_credits + ?),
                openai_photo_credits = max(0, openai_photo_credits + ?),
                photo_credits = max(0, photo_credits + ?),
                has_paid = CASE WHEN ? > 0 THEN 1 ELSE has_paid END
            WHERE user_id = ?
            """,
            (tot_add, np_add, ddg_add, oai_add, ddg_add + oai_add, tot_add, user_id),
        )

    cursor.execute(
        "SELECT credits, bonus_credits, no_photo_credits, ddg_photo_credits, openai_photo_credits FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    if row:
        return max(
            int(row["credits"] or 0),
            int(row["bonus_credits"] or 0)
            + int(row["no_photo_credits"] or 0)
            + int(row["ddg_photo_credits"] or 0)
            + int(row["openai_photo_credits"] or 0),
        )
    return max(0, credits_to_add)


def find_user_by_query(query: str) -> Optional[Dict[str, Any]]:
    q = query.strip().lstrip("@")
    conn = get_db_connection()
    cursor = conn.cursor()
    if q.isdigit():
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (int(q),))
    else:
        cursor.execute("SELECT * FROM users WHERE lower(username) = lower(?)", (q,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================================
# SUPPORT TICKETS & COMPLAINTS LOGGING (360° User History)
# ============================================================================

def log_support_ticket(user_id: int, message_text: str):
    if not user_id:
        return
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO support_tickets (user_id, message_text) VALUES (?, ?)",
        (user_id, (message_text or "").strip()),
    )
    conn.execute(
        "UPDATE users SET complaints_count = coalesce(complaints_count, 0) + 1 WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()


def get_user_full_history(user_id: int) -> Dict[str, Any]:
    """
    Returns full 360° user history for Admin card:
    - Profile & registration date
    - Total paid KZT & list of payments
    - Generated projects (with project IDs so Admin can delete any project)
    - Support / complaint messages count & recent messages
    """
    prof = get_user_profile(user_id)
    breakdown = get_user_credit_breakdown(user_id)
    conn = get_db_connection()

    pay_row = conn.execute(
        "SELECT coalesce(sum(amount_kzt), 0) as total_paid, count(*) as pay_cnt FROM payments WHERE user_id = ? AND status = 'approved'",
        (user_id,),
    ).fetchone()

    projects = [
        dict(r)
        for r in conn.execute(
            "SELECT id, topic, slide_count, design_id, created_at FROM user_projects WHERE user_id = ? ORDER BY id DESC LIMIT 8",
            (user_id,),
        ).fetchall()
    ]

    tickets = [
        dict(r)
        for r in conn.execute(
            "SELECT id, message_text, created_at FROM support_tickets WHERE user_id = ? ORDER BY id DESC LIMIT 5",
            (user_id,),
        ).fetchall()
    ]
    conn.close()

    return {
        "profile": prof,
        "credits_breakdown": breakdown,
        "total_paid_kzt": int(pay_row["total_paid"] or 0),
        "payments_count": int(pay_row["pay_cnt"] or 0),
        "projects": projects,
        "tickets": tickets,
        "complaints_count": max(int(prof.get("complaints_count") or 0), len(tickets)),
    }


def delete_user_project_by_id(project_id: int) -> Optional[Dict[str, Any]]:
    """Allows Admin to delete a specific user project."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM user_projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        conn.close()
        return None
    proj_dict = dict(row)
    conn.execute("DELETE FROM user_projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return proj_dict


# ============================================================================
# PAGINATED & FILTERED USER LIST + SEGMENTED BROADCAST
# ============================================================================

def get_users_paginated(
    page: int = 0,
    page_size: int = 8,
    filter_mode: str = "all",  # "all" | "photo" | "paid" | "active"
) -> Tuple[List[Dict[str, Any]], int]:
    conn = get_db_connection()
    where_clause = ""
    if filter_mode == "photo":
        where_clause = "WHERE user_id IN (SELECT DISTINCT user_id FROM generations WHERE with_photos = 1)"
    elif filter_mode == "paid":
        where_clause = "WHERE has_paid = 1 OR user_id IN (SELECT DISTINCT user_id FROM payments WHERE status = 'approved')"
    elif filter_mode == "active":
        where_clause = "WHERE last_active >= datetime('now', '-7 days')"

    total_row = conn.execute(f"SELECT count(*) as c FROM users {where_clause}").fetchone()
    total = int(total_row["c"] or 0)

    offset = max(0, page) * page_size
    rows = conn.execute(
        f"""
        SELECT user_id, username, first_name, credits, has_paid, created_at, last_active
        FROM users
        {where_clause}
        ORDER BY last_active DESC, user_id DESC
        LIMIT ? OFFSET ?
        """,
        (page_size, offset),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def get_segmented_user_ids(segment: str = "all") -> List[int]:
    """
    Returns user IDs for segmented broadcast:
    - 'all': Барлық қолданушылар
    - 'vip_paid': Тек VIP/Pro (төлем жасағандар)
    - 'photo_users': Тек фотомен презентация жасағандар
    - 'active_7d': Соңғы 7 күнде белсенділер
    """
    conn = get_db_connection()
    if segment == "vip_paid":
        rows = conn.execute(
            "SELECT user_id FROM users WHERE has_paid = 1 OR user_id IN (SELECT DISTINCT user_id FROM payments WHERE status = 'approved')"
        ).fetchall()
    elif segment == "photo_users":
        rows = conn.execute(
            "SELECT DISTINCT user_id FROM generations WHERE with_photos = 1"
        ).fetchall()
    elif segment == "active_7d":
        rows = conn.execute(
            "SELECT user_id FROM users WHERE last_active >= datetime('now', '-7 days')"
        ).fetchall()
    else:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [int(r["user_id"]) for r in rows if r["user_id"]]


# ============================================================================
# PARTNER WITHDRAWAL REQUESTS (MIN 2,000 ₸)
# ============================================================================

def create_withdrawal_request(user_id: int, amount_kzt: int, requisites: str) -> Tuple[Optional[int], str]:
    if amount_kzt < config.MIN_WITHDRAWAL_KZT:
        return None, f"⚠️ Шығарудың минималды сомасы — {config.MIN_WITHDRAWAL_KZT} ₸."

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT partner_balance_kzt FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or int(row["partner_balance_kzt"]) < amount_kzt:
        bal = int(row["partner_balance_kzt"]) if row else 0
        conn.close()
        return None, f"⚠️ Балансыңызда қаражат жеткіліксіз. Қолжетімді табыс: {bal} ₸."

    cursor.execute(
        """
        INSERT INTO withdrawals (user_id, amount_kzt, requisites, status)
        VALUES (?, ?, ?, 'pending')
        """,
        (user_id, amount_kzt, requisites.strip()),
    )
    w_id = cursor.lastrowid or 0
    conn.commit()
    conn.close()
    return w_id, ""


def approve_withdrawal_request(withdrawal_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
    w_row = cursor.fetchone()
    if not w_row or w_row["status"] != "pending":
        conn.close()
        return None

    user_id = w_row["user_id"]
    amount_kzt = int(w_row["amount_kzt"])
    requisites = w_row["requisites"]

    cursor.execute(
        "UPDATE withdrawals SET status = 'paid', processed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (withdrawal_id,),
    )
    cursor.execute(
        "UPDATE users SET partner_balance_kzt = max(0, partner_balance_kzt - ?) WHERE user_id = ?",
        (amount_kzt, user_id),
    )
    cursor.execute("SELECT partner_balance_kzt FROM users WHERE user_id = ?", (user_id,))
    u_row = cursor.fetchone()
    new_bal = int(u_row["partner_balance_kzt"]) if u_row else 0

    conn.commit()
    conn.close()
    return {
        "withdrawal_id": withdrawal_id,
        "user_id": user_id,
        "amount_kzt": amount_kzt,
        "requisites": requisites,
        "new_balance": new_bal,
    }


def reject_withdrawal_request(withdrawal_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
    w_row = cursor.fetchone()
    if not w_row or w_row["status"] != "pending":
        conn.close()
        return None

    cursor.execute(
        "UPDATE withdrawals SET status = 'rejected', processed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (withdrawal_id,),
    )
    conn.commit()
    conn.close()
    return dict(w_row)


def get_pending_withdrawals() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT w.*, u.username, u.first_name, u.partner_balance_kzt, u.invited_count, u.referral_sales_kzt
    FROM withdrawals w
    LEFT JOIN users u ON w.user_id = u.user_id
    WHERE w.status = 'pending'
    ORDER BY w.id ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ============================================================================
# PAYMENTS, 3-BUCKET CREDITS ALLOCATION & MANUAL RECEIPT APPROVAL
# ============================================================================

def is_receipt_duplicate(receipt_hash: str, receipt_number: Optional[str] = None) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    if receipt_hash:
        cursor.execute(
            "SELECT id FROM payments WHERE receipt_hash = ? AND status IN ('approved', 'pending') LIMIT 1",
            (receipt_hash,),
        )
        if cursor.fetchone():
            conn.close()
            return True

    if receipt_number:
        if receipt_used(receipt_number):
            conn.close()
            return True

    conn.close()
    return False


def create_payment_record(
    user_id: int,
    tariff_id: str,
    amount_kzt: int,
    credits_added: int,
    receipt_hash: str = "",
    receipt_number: str = "",
    status: str = "pending",
    no_photo_added: Optional[int] = None,
    ddg_photo_added: Optional[int] = None,
    openai_photo_added: Optional[int] = None,
    promo_code: Optional[str] = None,
) -> int:
    """Чек нөмірі бірегей болуы керек. Қайталау болса — 0 қайтарады."""
    tariffs = get_dynamic_tariffs()
    t_obj = tariffs.get(tariff_id, {})

    np_add = int(no_photo_added if no_photo_added is not None else t_obj.get("no_photo_credits", credits_added))
    ddg_add = int(ddg_photo_added if ddg_photo_added is not None else t_obj.get("ddg_photo_credits", 0))
    oai_add = int(openai_photo_added if openai_photo_added is not None else t_obj.get("openai_photo_credits", 0))
    tot_photo = ddg_add + oai_add

    conn = get_db_connection()
    cursor = conn.cursor()
    clean_rno = receipt_number.strip() if receipt_number and receipt_number.strip() else None
    try:
        cursor.execute(
            """
            INSERT INTO payments (
                user_id, tariff_id, amount_kzt, credits_added,
                no_photo_added, ddg_photo_added, openai_photo_added, photo_credits_added,
                promo_code, receipt_hash, receipt_number, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                tariff_id,
                amount_kzt,
                credits_added,
                np_add,
                ddg_add,
                oai_add,
                tot_photo,
                promo_code,
                receipt_hash,
                clean_rno,
                status,
            ),
        )
        payment_id = cursor.lastrowid or 0
        conn.commit()
        return payment_id
    except sqlite3.IntegrityError:
        logger.warning(f"Duplicate receipt_number={receipt_number}, user_id={user_id}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def approve_payment(payment_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    pay = cursor.fetchone()

    if not pay or pay["status"] != "pending":
        conn.close()
        return None

    user_id = pay["user_id"]
    amount_kzt = int(pay["amount_kzt"] or 0)
    credits_added = int(pay["credits_added"] or 0)
    tariff_id = pay["tariff_id"]
    np_add = int(pay["no_photo_added"] or 0)
    ddg_add = int(pay["ddg_photo_added"] or 0)
    oai_add = int(pay["openai_photo_added"] or 0)

    if np_add == 0 and ddg_add == 0 and oai_add == 0 and credits_added > 0:
        t_obj = get_dynamic_tariffs().get(tariff_id, {})
        np_add = int(t_obj.get("no_photo_credits", credits_added))
        ddg_add = int(t_obj.get("ddg_photo_credits", 0))
        oai_add = int(t_obj.get("openai_photo_credits", 0))

    cursor.execute(
        "UPDATE payments SET status = 'approved', approved_at = CURRENT_TIMESTAMP WHERE id = ?",
        (payment_id,),
    )
    cursor.execute(
        """
        UPDATE users
        SET credits = credits + ?,
            no_photo_credits = no_photo_credits + ?,
            ddg_photo_credits = ddg_photo_credits + ?,
            openai_photo_credits = openai_photo_credits + ?,
            photo_credits = photo_credits + ?,
            has_paid = 1,
            active_promo_code = NULL
        WHERE user_id = ?
        """,
        (credits_added, np_add, ddg_add, oai_add, ddg_add + oai_add, user_id),
    )

    cursor.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,))
    buyer_row = cursor.fetchone()
    referrer_id = buyer_row["referred_by"] if buyer_row else None

    partner_reward_kzt = 0
    referrer_sales_total = 0
    referrer_invited_total = 0

    if referrer_id:
        cursor.execute(
            "UPDATE users SET referral_sales_kzt = referral_sales_kzt + ? WHERE user_id = ?",
            (amount_kzt, referrer_id),
        )
        cursor.execute(
            "SELECT invited_count, referral_sales_kzt, partner_milestones_paid FROM users WHERE user_id = ?",
            (referrer_id,),
        )
        ref_row = cursor.fetchone()
        if ref_row:
            referrer_invited_total = ref_row["invited_count"]
            referrer_sales_total = ref_row["referral_sales_kzt"]
            milestones_paid = ref_row["partner_milestones_paid"]

            if referrer_invited_total >= config.PARTNER_MIN_INVITED_USERS:
                total_milestones = referrer_sales_total // config.PARTNER_SALES_THRESHOLD_KZT
                unpaid = total_milestones - milestones_paid
                if unpaid > 0:
                    partner_reward_kzt = unpaid * config.PARTNER_REWARD_KZT
                    cursor.execute(
                        """
                        UPDATE users
                        SET partner_milestones_paid = ?,
                            partner_balance_kzt = partner_balance_kzt + ?,
                            partner_total_earned_kzt = partner_total_earned_kzt + ?
                        WHERE user_id = ?
                        """,
                        (total_milestones, partner_reward_kzt, partner_reward_kzt, referrer_id),
                    )

    conn.commit()
    conn.close()

    new_breakdown = get_user_credit_breakdown(user_id)
    track_funnel_event(user_id, "payment_completed", {"tariff_id": tariff_id, "amount_kzt": amount_kzt})

    return {
        "payment_id": payment_id,
        "user_id": user_id,
        "tariff_id": tariff_id,
        "amount_kzt": amount_kzt,
        "credits_added": credits_added,
        "no_photo_added": np_add,
        "ddg_photo_added": ddg_add,
        "openai_photo_added": oai_add,
        "new_credits": new_breakdown["total"],
        "breakdown": new_breakdown,
        "referrer_id": referrer_id,
        "partner_reward_kzt": partner_reward_kzt,
        "referrer_sales_total": referrer_sales_total,
        "referrer_invited_total": referrer_invited_total,
    }


def reject_payment(payment_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    pay = cursor.fetchone()
    if not pay or pay["status"] != "pending":
        conn.close()
        return None
    cursor.execute("UPDATE payments SET status = 'rejected' WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()
    return dict(pay)


def get_recent_payments(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, u.username, u.first_name
    FROM payments p
    LEFT JOIN users u ON p.user_id = u.user_id
    ORDER BY p.id DESC
    LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def log_generation(
    user_id: int,
    topic: str,
    slide_count: int,
    design_id: str,
    format_type: str = "pptx",
    from_cache: bool = False,
    with_photos: bool = False,
    image_source: str = "none",
    language: str = "қазақша",
    template_id: str = "standard",
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO generations (user_id, topic, slide_count, design_id, format, from_cache, with_photos, image_source, language, template_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            topic,
            slide_count,
            design_id,
            format_type,
            1 if from_cache else 0,
            1 if with_photos else 0,
            image_source if with_photos else "none",
            language,
            template_id,
        ),
    )
    conn.commit()
    conn.close()
    track_funnel_event(
        user_id,
        "generation_completed",
        {"topic": topic, "slides": slide_count, "with_photos": with_photos, "language": language},
    )


# ============================================================================
# SMART CROSS-USER PRESENTATION CACHE (Redis + SQLite 30-day TTL)
# ============================================================================

def get_cached_presentation(
    topic: str,
    slide_count: int,
    doc_text: Optional[str] = None,
    language: str = "қазақша",
    template_id: str = "standard",
) -> Optional[PresentationData]:
    norm_topic = normalize_topic_key(topic)
    doc_hash = compute_doc_hash(doc_text)
    cache_key = f"{norm_topic}::{slide_count}::{doc_hash}::{language}::{template_id}"

    r_val = redis_get(f"pres_cache:{cache_key}")
    if r_val:
        try:
            return deserialize_presentation(r_val)
        except Exception:
            pass

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT presentation_json FROM presentation_cache
        WHERE (cache_key = ? OR cache_key = ?)
          AND updated_at >= datetime('now', '-30 days')
        LIMIT 1
        """,
        (cache_key, f"{norm_topic}::{slide_count}::{doc_hash}"),
    )
    row = cursor.fetchone()
    if row and row["presentation_json"]:
        cursor.execute(
            "UPDATE presentation_cache SET hit_count = hit_count + 1, updated_at = CURRENT_TIMESTAMP WHERE cache_key = ?",
            (cache_key,),
        )
        conn.commit()
        conn.close()
        try:
            return deserialize_presentation(row["presentation_json"])
        except Exception:
            return None

    conn.close()
    return None


def save_cached_presentation(
    topic: str,
    slide_count: int,
    presentation: PresentationData,
    doc_text: Optional[str] = None,
    language: str = "қазақша",
    template_id: str = "standard",
):
    norm_topic = normalize_topic_key(topic)
    doc_hash = compute_doc_hash(doc_text)
    cache_key = f"{norm_topic}::{slide_count}::{doc_hash}::{language}::{template_id}"
    pres_json = serialize_presentation(presentation)

    redis_set(f"pres_cache:{cache_key}", pres_json, ttl_seconds=3600 * 24 * 30)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO presentation_cache (cache_key, norm_topic, slide_count, doc_hash, presentation_json, hit_count)
    VALUES (?, ?, ?, ?, ?, 0)
    ON CONFLICT(cache_key) DO UPDATE SET
        presentation_json = excluded.presentation_json,
        updated_at = CURRENT_TIMESTAMP
    """, (cache_key, norm_topic, slide_count, doc_hash, pres_json))
    conn.commit()
    conn.close()


# ============================================================================
# SAVED USER PROJECTS ("📂 МЕНІҢ ЖОБАЛАРЫМ")
# ============================================================================

def save_user_project(user_id: int, presentation: PresentationData) -> int:
    if not user_id:
        return 0

    pres_json = serialize_presentation(presentation)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id FROM user_projects
    WHERE user_id = ? AND lower(topic) = lower(?) AND slide_count = ?
    ORDER BY id DESC LIMIT 1
    """, (user_id, presentation.topic, presentation.slide_count))
    existing = cursor.fetchone()

    if existing:
        proj_id = existing["id"]
        cursor.execute("""
        UPDATE user_projects
        SET design_id = ?, presentation_json = ?, created_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (presentation.design_id, pres_json, proj_id))
    else:
        cursor.execute("""
        INSERT INTO user_projects (user_id, topic, slide_count, design_id, presentation_json)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, presentation.topic, presentation.slide_count, presentation.design_id, pres_json))
        proj_id = cursor.lastrowid or 0

    conn.commit()
    conn.close()
    return proj_id


def get_user_projects(user_id: int, limit: int = 6, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT count(*) as total FROM user_projects WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()["total"]

    cursor.execute("""
    SELECT id, topic, slide_count, design_id, created_at
    FROM user_projects
    WHERE user_id = ?
    ORDER BY created_at DESC, id DESC
    LIMIT ? OFFSET ?
    """, (user_id, limit, offset))
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items, total


def get_user_project_by_id(project_id: int, user_id: Optional[int] = None) -> Optional[PresentationData]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute(
            "SELECT presentation_json, design_id FROM user_projects WHERE id = ? AND user_id = ?",
            (project_id, user_id),
        )
    else:
        cursor.execute(
            "SELECT presentation_json, design_id FROM user_projects WHERE id = ?",
            (project_id,),
        )
    row = cursor.fetchone()
    conn.close()
    if row and row["presentation_json"]:
        try:
            pres = deserialize_presentation(row["presentation_json"])
            pres.design_id = row["design_id"] or pres.design_id
            return pres
        except Exception:
            return None
    return None


# ============================================================================
# 7/30-DAY TIME SERIES, LOGICAL ALERTS & CSV/EXCEL DATABASE EXPORT
# ============================================================================

def get_time_series_stats(days: int = 7) -> Dict[str, Any]:
    """
    Computes daily Revenue (₸), New Users, and Generations over the last N days (7 or 30),
    plus Smart Logical Alerts ("🚨 Бүгін табыс 50% төмендеді!").
    """
    conn = get_db_connection()
    today = dt.date.today()
    dates: List[str] = [(today - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]

    rev_map: Dict[str, int] = {d: 0 for d in dates}
    usr_map: Dict[str, int] = {d: 0 for d in dates}
    gen_map: Dict[str, int] = {d: 0 for d in dates}

    for r in conn.execute(
        "SELECT date(coalesce(approved_at, created_at)) as d, coalesce(sum(amount_kzt), 0) as s FROM payments WHERE status = 'approved' GROUP BY d"
    ).fetchall():
        if r["d"] in rev_map:
            rev_map[r["d"]] = int(r["s"] or 0)

    for r in conn.execute("SELECT date(created_at) as d, count(*) as c FROM users GROUP BY d").fetchall():
        if r["d"] in usr_map:
            usr_map[r["d"]] = int(r["c"] or 0)

    for r in conn.execute("SELECT date(created_at) as d, count(*) as c FROM generations GROUP BY d").fetchall():
        if r["d"] in gen_map:
            gen_map[r["d"]] = int(r["c"] or 0)

    conn.close()

    revenues = [rev_map[d] for d in dates]
    users_series = [usr_map[d] for d in dates]
    gens_series = [gen_map[d] for d in dates]

    alerts: List[str] = []
    if len(revenues) >= 2:
        today_rev = revenues[-1]
        yest_rev = revenues[-2]
        if yest_rev > 0 and today_rev <= yest_rev * 0.5:
            alerts.append(f"🚨 <b>Ескерту:</b> Бүгін табыс кешегіден 50%-дан астам төмендеді ({yest_rev:,} ₸ → {today_rev:,} ₸)!")
        elif today_rev > yest_rev and yest_rev > 0:
            pct_up = int(((today_rev - yest_rev) / yest_rev) * 100)
            alerts.append(f"📈 <b>Оң динамика:</b> Бүгін табыс кешегіден +{pct_up}% өсті ({today_rev:,} ₸)!")

    ai_stats = get_ai_cost_stats()
    if revenues and revenues[-1] > 0 and ai_stats["today_kzt"] > revenues[-1] * 0.35:
        alerts.append(f"⚠️ <b>AI шығыны ескертуі:</b> Бүгінгі AI шығыны ({ai_stats['today_kzt']} ₸) табыстың 35%-ынан асты.")

    if not alerts:
        alerts.append("✅ <b>Жүйе қалыпты:</b> Табыс пен AI шығындарында ауытқу жоқ.")

    return {
        "days": days,
        "dates": dates,
        "revenues": revenues,
        "new_users": users_series,
        "generations": gens_series,
        "alerts": alerts,
    }


def export_database_zip_bytes() -> Tuple[bytes, str]:
    """
    Exports all key tables (users, payments, generations, ai_usage_logs, promo_codes)
    as Excel-compatible UTF-8-BOM .CSV files bundled in a clean .ZIP archive.
    """
    conn = get_db_connection()
    tables = [
        ("users.csv", "SELECT * FROM users ORDER BY user_id DESC"),
        ("payments.csv", "SELECT * FROM payments ORDER BY id DESC"),
        ("generations.csv", "SELECT * FROM generations ORDER BY id DESC"),
        ("ai_costs.csv", "SELECT * FROM ai_usage_logs ORDER BY id DESC"),
        ("promo_codes.csv", "SELECT * FROM promo_codes ORDER BY code ASC"),
    ]

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, query in tables:
            try:
                rows = conn.execute(query).fetchall()
                s_io = io.StringIO()
                s_io.write("\ufeff")  # UTF-8 BOM so Microsoft Excel opens Cyrillic cleanly
                writer = csv.writer(s_io)
                if rows:
                    writer.writerow(rows[0].keys())
                    for r in rows:
                        writer.writerow([r[k] for k in r.keys()])
                else:
                    writer.writerow(["Деректер жоқ"])
                zf.writestr(fname, s_io.getvalue().encode("utf-8"))
            except Exception as e:
                zf.writestr(fname, f"Error: {e}".encode("utf-8"))
    conn.close()
    filename = f"bot_database_export_{dt.date.today().isoformat()}.zip"
    return zip_buf.getvalue(), filename


# ============================================================================
# ADMIN ANALYTICS (Including Logical Alerts, AI Costs, Funnel & Promo Codes)
# ============================================================================

def get_admin_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT count(*) as total FROM users")
    total_users = cursor.fetchone()["total"]

    cursor.execute("SELECT count(*) as today FROM users WHERE date(last_active) = date('now')")
    users_today = cursor.fetchone()["today"]

    cursor.execute("SELECT count(*) as total FROM generations")
    total_generations = cursor.fetchone()["total"]

    cursor.execute("SELECT count(*) as today FROM generations WHERE date(created_at) = date('now')")
    generations_today = cursor.fetchone()["today"]

    cursor.execute("SELECT count(*) as cached FROM generations WHERE from_cache = 1")
    cached_generations = cursor.fetchone()["cached"]

    cursor.execute("SELECT count(*) as photo_gens FROM generations WHERE with_photos = 1")
    photo_generations = cursor.fetchone()["photo_gens"]

    cursor.execute("SELECT count(*) as total_cached_items FROM presentation_cache")
    total_cached_items = cursor.fetchone()["total_cached_items"]

    cursor.execute(
        "SELECT coalesce(sum(amount_kzt), 0) as rev, count(*) as cnt FROM payments WHERE status = 'approved'"
    )
    rev_total_row = cursor.fetchone()
    revenue_total_kzt = rev_total_row["rev"]
    payments_total_count = rev_total_row["cnt"]

    cursor.execute(
        "SELECT coalesce(sum(amount_kzt), 0) as rev, count(*) as cnt FROM payments WHERE status = 'approved' AND date(approved_at) = date('now')"
    )
    rev_today_row = cursor.fetchone()
    revenue_today_kzt = rev_today_row["rev"]
    payments_today_count = rev_today_row["cnt"]

    cursor.execute("SELECT count(*) as pend_cnt FROM payments WHERE status = 'pending'")
    pending_payments_count = cursor.fetchone()["pend_cnt"]

    cursor.execute("""
    SELECT tariff_id, count(*) as cnt, coalesce(sum(amount_kzt), 0) as sum_kzt
    FROM payments
    WHERE status = 'approved'
    GROUP BY tariff_id
    """)
    packages_breakdown = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT coalesce(sum(partner_total_earned_kzt), 0) as partner_paid FROM users")
    partner_paid_kzt = cursor.fetchone()["partner_paid"]

    cursor.execute(
        "SELECT count(*) as cnt, coalesce(sum(amount_kzt), 0) as sum_kzt FROM withdrawals WHERE status = 'pending'"
    )
    w_pend = cursor.fetchone()
    pending_withdrawals_count = w_pend["cnt"]
    pending_withdrawals_kzt = w_pend["sum_kzt"]

    cursor.execute(
        "SELECT count(*) as cnt, coalesce(sum(amount_kzt), 0) as sum_kzt FROM withdrawals WHERE status = 'paid'"
    )
    w_paid = cursor.fetchone()
    paid_withdrawals_count = w_paid["cnt"]
    paid_withdrawals_kzt = w_paid["sum_kzt"]

    cursor.execute("""
    SELECT design_id, count(*) as count
    FROM generations
    GROUP BY design_id
    ORDER BY count DESC
    LIMIT 5
    """)
    top_themes = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
    SELECT g.topic, g.slide_count, g.design_id, g.format, g.from_cache, g.with_photos, g.image_source, g.language, g.created_at, u.first_name, u.username
    FROM generations g
    LEFT JOIN users u ON g.user_id = u.user_id
    ORDER BY g.id DESC
    LIMIT 10
    """)
    recent_generations = [dict(row) for row in cursor.fetchall()]

    conn.close()

    funnel = get_funnel_stats()
    ai_costs = get_ai_cost_stats()
    ts_7d = get_time_series_stats(7)

    return {
        "total_users": total_users,
        "users_today": users_today,
        "total_generations": total_generations,
        "generations_today": generations_today,
        "cached_generations": cached_generations,
        "photo_generations": photo_generations,
        "total_cached_items": total_cached_items,
        "revenue_total_kzt": revenue_total_kzt,
        "payments_total_count": payments_total_count,
        "revenue_today_kzt": revenue_today_kzt,
        "payments_today_count": payments_today_count,
        "pending_payments_count": pending_payments_count,
        "packages_breakdown": packages_breakdown,
        "partner_paid_kzt": partner_paid_kzt,
        "pending_withdrawals_count": pending_withdrawals_count,
        "pending_withdrawals_kzt": pending_withdrawals_kzt,
        "paid_withdrawals_count": paid_withdrawals_count,
        "paid_withdrawals_kzt": paid_withdrawals_kzt,
        "top_themes": top_themes,
        "recent_generations": recent_generations,
        "funnel": funnel,
        "ai_costs": ai_costs,
        "logical_alerts": ts_7d["alerts"],
    }


def get_all_user_ids() -> List[int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    user_ids = [row["user_id"] for row in cursor.fetchall()]
    conn.close()
    return user_ids
