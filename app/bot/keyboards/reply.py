"""
Persistent reply keyboard for Telegram Bot.
Includes "📂 Менің жобаларым", "🎨 Дизайн таңдау", "📄 Бет саны", and "❓ Көмек".
"""
from typing import Dict, Any


def get_persistent_reply_keyboard() -> Dict[str, Any]:
    """Returns persistent bottom reply keyboard dictionary (compatible with Telegram Bot API)."""
    return {
        "keyboard": [
            [{"text": "📂 Менің жобаларым"}, {"text": "🎨 Дизайн таңдау"}],
            [{"text": "📄 Бет саны"}, {"text": "❓ Көмек"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }
