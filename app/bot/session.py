"""
Persistent + Redis + SQLite session manager for Telegram users.
Сессия жадыда, Redis-те (егер REDIS_URL қосылған болса) ЖӘНЕ SQLite-те сақталады.
"""
import json
import sqlite3
from typing import Dict
from app.core.types import TelegramSession, PresentationData
from app.core.db import DB_PATH, get_db_connection
from app.core.redis_cache import redis_get, redis_set
import config

_sessions: Dict[int, TelegramSession] = {}


def init_sessions_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            chat_id INTEGER PRIMARY KEY,
            slide_count INTEGER DEFAULT 15,
            design_id TEXT DEFAULT 'auto',
            language TEXT DEFAULT 'қазақша',
            template_id TEXT DEFAULT 'standard',
            with_photos INTEGER DEFAULT 0,
            image_source TEXT DEFAULT 'ddg',
            active_promo_code TEXT DEFAULT NULL,
            pending_topic TEXT,
            pending_tariff_id TEXT,
            last_presentation_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for mig in (
        "ALTER TABLE user_sessions ADD COLUMN language TEXT DEFAULT 'қазақша'",
        "ALTER TABLE user_sessions ADD COLUMN template_id TEXT DEFAULT 'standard'",
        "ALTER TABLE user_sessions ADD COLUMN with_photos INTEGER DEFAULT 0",
        "ALTER TABLE user_sessions ADD COLUMN image_source TEXT DEFAULT 'ddg'",
        "ALTER TABLE user_sessions ADD COLUMN active_promo_code TEXT DEFAULT NULL",
    ):
        try:
            conn.execute(mig)
        except Exception:
            pass
    conn.commit()
    conn.close()


def _serialize_presentation(pres: PresentationData) -> str:
    if hasattr(pres, "model_dump_json"):
        return pres.model_dump_json()
    return pres.json()


def _deserialize_presentation(raw_json: str) -> PresentationData:
    if hasattr(PresentationData, "model_validate_json"):
        return PresentationData.model_validate_json(raw_json)
    return PresentationData.parse_raw(raw_json)


def _serialize_session(session: TelegramSession) -> str:
    if hasattr(session, "model_dump_json"):
        return session.model_dump_json()
    return session.json()


def _deserialize_session(raw_json: str) -> TelegramSession:
    if hasattr(TelegramSession, "model_validate_json"):
        return TelegramSession.model_validate_json(raw_json)
    return TelegramSession.parse_raw(raw_json)


def get_telegram_session(chat_id: int) -> TelegramSession:
    """Retrieve from memory, Redis, or SQLite, or create new session."""
    if chat_id in _sessions:
        return _sessions[chat_id]

    # Try Redis
    r_raw = redis_get(f"session:{chat_id}")
    if r_raw:
        try:
            s = _deserialize_session(r_raw)
            _sessions[chat_id] = s
            return s
        except Exception:
            pass

    init_sessions_table()
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM user_sessions WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        conn.close()
        if row:
            row_d = dict(row)
            last_pres = None
            if row_d.get("last_presentation_json"):
                try:
                    last_pres = _deserialize_presentation(row_d["last_presentation_json"])
                except Exception:
                    pass
            s = TelegramSession(
                slideCount=row_d.get("slide_count") or config.DEFAULT_SLIDE_COUNT,
                designId=row_d.get("design_id") or "auto",
                language=row_d.get("language") or "қазақша",
                templateId=row_d.get("template_id") or "standard",
                withPhotos=bool(row_d.get("with_photos")),
                imageSource=row_d.get("image_source") or "ddg",
                activePromoCode=row_d.get("active_promo_code"),
                pendingTopic=row_d.get("pending_topic"),
                pendingTariffId=row_d.get("pending_tariff_id"),
                lastPresentation=last_pres,
            )
            _sessions[chat_id] = s
            return s
    except Exception:
        pass

    _sessions[chat_id] = TelegramSession(
        slideCount=config.DEFAULT_SLIDE_COUNT,
        designId="auto",
        themePage=0,
    )
    return _sessions[chat_id]


def save_session(chat_id: int, session: TelegramSession):
    """Save session changes to Redis and SQLite."""
    _sessions[chat_id] = session
    try:
        redis_set(f"session:{chat_id}", _serialize_session(session), ttl_seconds=86400 * 7)
    except Exception:
        pass

    init_sessions_table()
    try:
        pres_json = (
            _serialize_presentation(session.lastPresentation)
            if session.lastPresentation
            else None
        )
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO user_sessions (
                chat_id, slide_count, design_id, language, template_id,
                with_photos, image_source, active_promo_code,
                pending_topic, pending_tariff_id, last_presentation_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                slide_count = excluded.slide_count,
                design_id = excluded.design_id,
                language = excluded.language,
                template_id = excluded.template_id,
                with_photos = excluded.with_photos,
                image_source = excluded.image_source,
                active_promo_code = excluded.active_promo_code,
                pending_topic = excluded.pending_topic,
                pending_tariff_id = excluded.pending_tariff_id,
                last_presentation_json = excluded.last_presentation_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                chat_id,
                session.slideCount,
                session.designId,
                session.language,
                session.templateId,
                1 if session.withPhotos else 0,
                session.imageSource,
                session.activePromoCode,
                session.pendingTopic,
                session.pendingTariffId,
                pres_json,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def flush_session(chat_id: int):
    """Persist current in-memory session for chat_id if present."""
    if chat_id in _sessions:
        save_session(chat_id, _sessions[chat_id])
