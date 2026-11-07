"""
In-memory session manager for Telegram users.
"""
from typing import Dict
from app.core.types import TelegramSession
import config

_sessions: Dict[int, TelegramSession] = {}

def get_telegram_session(chat_id: int) -> TelegramSession:
    """Retrieve or create user session."""
    if chat_id not in _sessions:
        _sessions[chat_id] = TelegramSession(
            slideCount=config.DEFAULT_SLIDE_COUNT,
            designId="auto",
            themePage=0,
        )
    return _sessions[chat_id]
