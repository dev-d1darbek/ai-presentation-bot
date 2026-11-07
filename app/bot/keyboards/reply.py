"""
Persistent reply keyboard for Telegram Bot.
"""
from typing import Dict, Any

def get_persistent_reply_keyboard() -> Dict[str, Any]:
    """Returns persistent bottom reply keyboard dictionary (compatible with Telegram Bot API)."""
    return {
        "keyboard": [
            [{"text": "🎨 Дизайн таңдау"}, {"text": "📄 Бет саны"}],
            [{"text": "❓ Көмек"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }
