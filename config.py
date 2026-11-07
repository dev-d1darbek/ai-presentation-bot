"""
Configuration settings for AI Presentation Bot.
Loads from environment variables or .env file.
"""
import os
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY", "").strip() or None
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "").strip() or None
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "").strip() or None

DEFAULT_SLIDE_COUNT: int = int(os.getenv("DEFAULT_SLIDE_COUNT", "15"))
DEFAULT_THEME_ID: str = os.getenv("DEFAULT_THEME_ID", "swiss_minimalism")
MAX_SLIDE_COUNT: int = 30
MIN_SLIDE_COUNT: int = 3

# Admin Telegram user IDs (comma-separated, e.g. "123456789,987654321")
raw_admins = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS: List[int] = []
if raw_admins:
    for aid in raw_admins.split(","):
        aid_clean = aid.strip()
        if aid_clean.isdigit():
            ADMIN_IDS.append(int(aid_clean))
