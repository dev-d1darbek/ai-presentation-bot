"""
Persistent reply keyboard for Telegram Bot (Commercial Pro v2 Edition).
Removed TTS button as requested; includes Projects, Balance/Tariffs, Templates, Design, Slide Count, Referral, and Support.
"""
from typing import Dict, Any


def get_persistent_reply_keyboard() -> Dict[str, Any]:
    """Returns persistent bottom reply keyboard dictionary."""
    return {
        "keyboard": [
            [{"text": "📂 Менің жобаларым"}, {"text": "💳 Баланс / Тарифтер"}],
            [{"text": "📐 Үлгілер (Шаблон)"}, {"text": "🎨 Дизайн таңдау"}],
            [{"text": "📄 Бет саны"}, {"text": "👥 Реферал (Табыс табу)"}],
            [{"text": "👨‍💻 Админмен байланыс"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }
