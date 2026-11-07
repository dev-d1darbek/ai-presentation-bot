"""
SQLite Database for:
1. Dynamic Settings ('seller' company + BIN from 1st receipt, 'kaspi_pay_url', dynamic 'tariffs' prices)
2. Receipts Anti-Fraud Table ('receipts' table matching test.py)
3. User Tracking, Credits Balance, Referral System & Student Partner Earnings
4. Partner Withdrawal Requests (min 2,000 ₸, custom amount, Kaspi phone/card, Admin "Төленді" deduction)
5. Saved User Projects ("📂 Менің жобаларым") & Smart Cross-User Presentation Cache
6. Advanced Admin Panel Analytics & User Lookup
"""
import copy
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
from typing import Dict, Any, List, Optional, Tuple

import config
from app.core.types import PresentationData

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
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
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
    """Initializes all tables and columns if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Exact tables from test.py (settings & receipts)
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
        referred_by INTEGER DEFAULT NULL,
        invited_count INTEGER DEFAULT 0,
        referral_sales_kzt INTEGER DEFAULT 0,
        partner_milestones_paid INTEGER DEFAULT 0,
        partner_balance_kzt INTEGER DEFAULT 0,
        partner_total_earned_kzt INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    user_migrations = [
        f"ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT {config.WELCOME_FREE_CREDITS}",
        "ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN invited_count INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN referral_sales_kzt INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN partner_milestones_paid INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN partner_balance_kzt INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN partner_total_earned_kzt INTEGER DEFAULT 0",
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
        receipt_hash TEXT,
        receipt_number TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP DEFAULT NULL
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    try:
        cursor.execute("ALTER TABLE generations ADD COLUMN from_cache INTEGER DEFAULT 0")
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
# DYNAMIC SETTINGS, SELLER AUTO-MEMORIZATION & RECEIPTS (test.py integration)
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
    """Returns saved seller dict {'company': ..., 'company_bin': ..., 'sample_receipt': ...} or None."""
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
    """Returns the dynamic Kaspi Pay link set by Admin in bot (or fallback from .env)."""
    saved = get_setting("kaspi_pay_url")
    if saved and saved.strip():
        return saved.strip()
    return config.KASPI_PAY_URL


def set_kaspi_pay_url(url: str):
    set_setting("kaspi_pay_url", url.strip())


def get_dynamic_tariffs() -> Dict[str, Dict[str, Any]]:
    """
    Returns dynamic tariff plans (editable by Admin inside the bot).
    """
    raw = get_setting("tariffs")
    base = copy.deepcopy(config.TARIFF_PLANS)
    if raw:
        try:
            saved = json.loads(raw)
            for k, v in saved.items():
                if k in base and isinstance(v, dict):
                    base[k].update(v)
        except Exception:
            pass
    return base


def update_tariff_setting(tariff_id: str, price_kzt: int, credits: Optional[int] = None) -> Dict[str, Any]:
    """
    Updates a tariff's price (and optionally its presentation count) in SQLite settings.
    """
    tariffs = get_dynamic_tariffs()
    if tariff_id not in tariffs:
        tariff_id = "hit"
    tariffs[tariff_id]["price_kzt"] = int(price_kzt)
    if credits is not None and credits > 0:
        tariffs[tariff_id]["credits"] = int(credits)
        tariffs[tariff_id]["description"] = f"{int(credits)} презентация + барлық функциялар"
    set_setting("tariffs", json.dumps(tariffs, ensure_ascii=False))
    return tariffs[tariff_id]


def receipt_used(rno: str) -> bool:
    """Checks if a Kaspi receipt number was already used (checks both receipts and payments tables)."""
    if not rno:
        return False
    conn = get_db_connection()
    r1 = conn.execute("SELECT 1 FROM receipts WHERE receipt_no = ?", (rno,)).fetchone()
    r2 = conn.execute(
        "SELECT 1 FROM payments WHERE receipt_number = ? AND status = 'approved'", (rno,)
    ).fetchone()
    conn.close()
    return (r1 is not None) or (r2 is not None)


def save_receipt(uid: int, rno: str, amount: int, bin_: str) -> bool:
    """Saves a verified Kaspi receipt number into receipts table."""
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
# USER REGISTRATION, CREDITS & REFERRAL / PARTNER SYSTEM
# ============================================================================

def log_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    referrer_id: Optional[int] = None,
) -> Dict[str, Any]:
    result = {
        "is_new": False,
        "referrer_id": None,
        "free_slide_awarded": False,
        "referrer_invited_count": 0,
        "partner_reward_kzt": 0,
    }
    if not user_id:
        return result

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            """
            UPDATE users
            SET username = coalesce(?, username),
                first_name = coalesce(?, first_name),
                last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (username, first_name, user_id),
        )
        conn.commit()
        conn.close()
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

    cursor.execute(
        """
        INSERT INTO users (user_id, username, first_name, credits, referred_by, last_active)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (user_id, username, first_name, config.WELCOME_FREE_CREDITS, valid_referrer),
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
                "UPDATE users SET credits = credits + 1 WHERE user_id = ?",
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
    if not row:
        log_user(user_id)
        return get_user_profile(user_id)
    return dict(row)


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


def get_user_credits(user_id: int) -> int:
    profile = get_user_profile(user_id)
    return int(profile.get("credits", 0))


def consume_user_credit(user_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET credits = credits - 1 WHERE user_id = ? AND credits > 0",
        (user_id,),
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def add_user_credits(user_id: int, credits_to_add: int) -> int:
    log_user(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET credits = max(0, credits + ?) WHERE user_id = ?",
        (credits_to_add, user_id),
    )
    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    new_credits = int(row["credits"]) if row else max(0, credits_to_add)
    conn.commit()
    conn.close()
    return new_credits


# ============================================================================
# PARTNER WITHDRAWAL REQUESTS (ШЫҒАРУ СҰРАНЫСТАРЫ — MIN 2,000 ₸)
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
# PAYMENTS & PARTNER COMMISSION ENGINE
# ============================================================================

def is_receipt_duplicate(receipt_hash: str, receipt_number: Optional[str] = None) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    if receipt_hash:
        cursor.execute(
            "SELECT id FROM payments WHERE receipt_hash = ? AND status = 'approved' LIMIT 1",
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
) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO payments (user_id, tariff_id, amount_kzt, credits_added, receipt_hash, receipt_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, tariff_id, amount_kzt, credits_added, receipt_hash, receipt_number, status),
    )
    payment_id = cursor.lastrowid or 0
    conn.commit()
    conn.close()
    return payment_id


def approve_payment(payment_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    pay = cursor.fetchone()
    if not pay or pay["status"] == "approved":
        conn.close()
        return None

    user_id = pay["user_id"]
    amount_kzt = pay["amount_kzt"]
    credits_added = pay["credits_added"]
    tariff_id = pay["tariff_id"]

    cursor.execute(
        "UPDATE payments SET status = 'approved', approved_at = CURRENT_TIMESTAMP WHERE id = ?",
        (payment_id,),
    )
    cursor.execute(
        "UPDATE users SET credits = credits + ? WHERE user_id = ?",
        (credits_added, user_id),
    )
    cursor.execute("SELECT credits, referred_by FROM users WHERE user_id = ?", (user_id,))
    buyer_row = cursor.fetchone()
    new_credits = buyer_row["credits"] if buyer_row else credits_added
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

    return {
        "payment_id": payment_id,
        "user_id": user_id,
        "tariff_id": tariff_id,
        "amount_kzt": amount_kzt,
        "credits_added": credits_added,
        "new_credits": new_credits,
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
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO generations (user_id, topic, slide_count, design_id, format, from_cache)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, topic, slide_count, design_id, format_type, 1 if from_cache else 0))
    conn.commit()
    conn.close()


# ============================================================================
# SMART CROSS-USER PRESENTATION CACHE
# ============================================================================

def get_cached_presentation(
    topic: str,
    slide_count: int,
    doc_text: Optional[str] = None,
) -> Optional[PresentationData]:
    norm_topic = normalize_topic_key(topic)
    doc_hash = compute_doc_hash(doc_text)
    cache_key = f"{norm_topic}::{slide_count}::{doc_hash}"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT presentation_json FROM presentation_cache WHERE cache_key = ?",
        (cache_key,),
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
):
    norm_topic = normalize_topic_key(topic)
    doc_hash = compute_doc_hash(doc_text)
    cache_key = f"{norm_topic}::{slide_count}::{doc_hash}"
    pres_json = serialize_presentation(presentation)

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
# ADMIN ANALYTICS (INCLUDING REVENUE, SALES & WITHDRAWALS)
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
    SELECT slide_count, count(*) as count
    FROM generations
    GROUP BY slide_count
    ORDER BY count DESC
    LIMIT 5
    """)
    top_slide_counts = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
    SELECT g.topic, g.slide_count, g.design_id, g.format, g.from_cache, g.created_at, u.first_name, u.username
    FROM generations g
    LEFT JOIN users u ON g.user_id = u.user_id
    ORDER BY g.id DESC
    LIMIT 10
    """)
    recent_generations = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "total_users": total_users,
        "users_today": users_today,
        "total_generations": total_generations,
        "generations_today": generations_today,
        "cached_generations": cached_generations,
        "total_cached_items": total_cached_items,
        "revenue_total_kzt": revenue_total_kzt,
        "payments_total_count": payments_total_count,
        "revenue_today_kzt": revenue_today_kzt,
        "payments_today_count": payments_today_count,
        "packages_breakdown": packages_breakdown,
        "partner_paid_kzt": partner_paid_kzt,
        "pending_withdrawals_count": pending_withdrawals_count,
        "pending_withdrawals_kzt": pending_withdrawals_kzt,
        "paid_withdrawals_count": paid_withdrawals_count,
        "paid_withdrawals_kzt": paid_withdrawals_kzt,
        "top_themes": top_themes,
        "top_slide_counts": top_slide_counts,
        "recent_generations": recent_generations,
    }


def get_all_user_ids() -> List[int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    user_ids = [row["user_id"] for row in cursor.fetchall()]
    conn.close()
    return user_ids
