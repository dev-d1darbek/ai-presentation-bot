"""
Persistent reply keyboard for Telegram Bot.
Includes Projects, Balance/Tariffs, Referral/Partner Earnings, Design, Slide Count, and Admin Support.
"""
from typing import Dict, Any


def get_persistent_reply_keyboard() -> Dict[str, Any]:
    """Returns persistent bottom reply keyboard dictionary."""
    return {
        "keyboard": [
            [{"text": "📂 Менің жобаларым"}, {"text": "💳 Баланс / Тарифтер"}],
            [{"text": "👥 Реферал (Табыс табу)"}, {"text": "🎨 Дизайн таңдау"}],
            [{"text": "📄 Бет саны"}, {"text": "👨‍💻 Админмен байланыс"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }
