"""
SQLite Database for:
1. User Tracking & Admin Analytics
2. Saved User Projects ("📂 Менің жобаларым" — retrieve & download anytime)
3. Smart Cross-User Presentation Cache (If user1 generates topic X with N slides,
   and user2 later requests topic X with N slides — even with a different design —
   it loads instantly from cache in 0.01s and re-renders in the new design without calling AI!)
"""
import hashlib
import json
import os
import re
import sqlite3
from typing import Dict, Any, List, Optional, Tuple

from app.core.types import PresentationData

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "bot.db")


def serialize_presentation(presentation: PresentationData) -> str:
    """Compatible with both Pydantic v1 and Pydantic v2."""
    if hasattr(presentation, "model_dump"):
        return json.dumps(presentation.model_dump(), ensure_ascii=False)
    return json.dumps(presentation.dict(), ensure_ascii=False)


def deserialize_presentation(raw_json: str) -> PresentationData:
    """Compatible with both Pydantic v1 and Pydantic v2."""
    data = json.loads(raw_json)
    if hasattr(PresentationData, "model_validate"):
        return PresentationData.model_validate(data)
    return PresentationData.parse_obj(data)


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_topic_key(topic: str) -> str:
    """
    Normalizes topic string for cross-user cache matching:
    lowercase, collapse spaces, strip punctuation.
    """
    clean = topic.lower().strip()
    clean = re.sub(r"[^\w\s\u0400-\u04FF]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def compute_doc_hash(doc_text: Optional[str]) -> str:
    """Computes SHA-256 short hash for uploaded document text (or empty string if none)."""
    if not doc_text or not doc_text.strip():
        return ""
    return hashlib.sha256(doc_text.strip().encode("utf-8", errors="ignore")).hexdigest()[:16]


def init_db():
    """Initializes all tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def log_user(user_id: int, username: Optional[str] = None, first_name: Optional[str] = None):
    """Logs or updates user activity."""
    if not user_id:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO users (user_id, username, first_name, last_active)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(user_id) DO UPDATE SET
        username=coalesce(?, users.username),
        first_name=coalesce(?, users.first_name),
        last_active=CURRENT_TIMESTAMP
    """, (user_id, username, first_name, username, first_name))
    conn.commit()
    conn.close()


def log_generation(
    user_id: int,
    topic: str,
    slide_count: int,
    design_id: str,
    format_type: str = "pptx",
    from_cache: bool = False,
):
    """Logs presentation generation."""
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
    """
    Checks if any user has already generated a presentation with the same normalized
    topic, slide_count, and document hash. If found, increments hit_count and returns it.
    """
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
    """Saves generated presentation to the cross-user global cache."""
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
    """
    Saves a presentation to the user's personal project history.
    If the user already has a project with the exact same topic and slide_count,
    updates it instead of duplicating.
    Returns the project ID.
    """
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
    """
    Returns (list of user's saved project summaries, total count).
    """
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
    """Loads a saved project by its ID."""
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
# ADMIN ANALYTICS
# ============================================================================

def get_admin_stats() -> Dict[str, Any]:
    """Retrieves aggregated statistics for /admin dashboard."""
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
        "top_themes": top_themes,
        "top_slide_counts": top_slide_counts,
        "recent_generations": recent_generations,
    }


def get_all_user_ids() -> List[int]:
    """Returns all user IDs for broadcasting announcements."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    user_ids = [row["user_id"] for row in cursor.fetchall()]
    conn.close()
    return user_ids
