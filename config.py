"""
Configuration settings for AI Presentation Bot.
Loads from environment variables or .env file.
"""
import os
from typing import Optional, List, Dict, Any
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

# Welcome & Referral Rules
WELCOME_FREE_CREDITS: int = int(os.getenv("WELCOME_FREE_CREDITS", "1"))
REFERRAL_FRIENDS_FOR_FREE_SLIDE: int = 2
PARTNER_MIN_INVITED_USERS: int = 20
PARTNER_SALES_THRESHOLD_KZT: int = 10000
PARTNER_REWARD_KZT: int = 2000
MIN_WITHDRAWAL_KZT: int = int(os.getenv("MIN_WITHDRAWAL_KZT", "2000"))

# Kaspi Pay Fiscal Verifier Settings
KASPI_PAY_URL: str = os.getenv("KASPI_PAY_URL", "https://pay.kaspi.kz/pay/YOUR_KASPI_LINK").strip()
KASPI_BIN: str = os.getenv("KASPI_BIN", "").strip()  # Сатушының 12 таңбалы ЖСН/БСН (ИИН/БИН продавца)
KASPI_PHONE: str = os.getenv("KASPI_PHONE", "+7 777 000 00 00").strip()
KASPI_RECIPIENT_NAME: str = os.getenv("KASPI_RECIPIENT_NAME", "").strip()

# Admin Support Contact (@username)
ADMIN_CONTACT: str = os.getenv("ADMIN_CONTACT", "").strip()

# Tariff Plans
TARIFF_PLANS: Dict[str, Dict[str, Any]] = {
    "single": {
        "id": "single",
        "title": "«Бір реттік»",
        "price_kzt": 200,
        "credits": 1,
        "description": "1 презентация + PDF + Қорғау сөзі",
    },
    "hit": {
        "id": "hit",
        "title": "«Студент (Хит)»",
        "price_kzt": 2000,
        "credits": 15,
        "description": "15 презентация + барлық функциялар",
    },
    "vip": {
        "id": "vip",
        "title": "«Студент (VIP)»",
        "price_kzt": 5000,
        "credits": 40,
        "description": "40 презентация + барлық функциялар",
    },
}

# Admin Telegram user IDs (comma-separated, e.g. "123456789,987654321")
raw_admins = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS: List[int] = []
if raw_admins:
    for aid in raw_admins.split(","):
        aid_clean = aid.strip()
        if aid_clean.isdigit():
            ADMIN_IDS.append(int(aid_clean))
