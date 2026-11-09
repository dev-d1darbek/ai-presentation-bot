"""
Persistent reply keyboard for Telegram Bot (Bilingual: Kazakh 'kk' & Russian 'ru').
Includes '➕ Жаңа презентация жасау' / '➕ Создать новую презентацию' at the top to restart the 3-direction wizard anytime.
"""
from typing import Dict, Any


def get_persistent_reply_keyboard(ui_lang: str = "kk") -> Dict[str, Any]:
    """Returns persistent bottom reply keyboard dictionary in Kazakh ('kk') or Russian ('ru')."""
    if str(ui_lang).lower().strip() == "ru":
        return {
            "keyboard": [
                [{"text": "➕ Создать новую презентацию"}],
                [{"text": "📂 Мои проекты"}, {"text": "💳 Баланс / Тарифы"}],
                [{"text": "🎨 Выбрать дизайн"}, {"text": "📐 Шаблоны"}],
                [{"text": "👥 Рефералы (Заработок)"}, {"text": "🌐 Тіл / Язык"}],
                [{"text": "👨‍💻 Связь с админом"}],
            ],
            "resize_keyboard": True,
            "is_persistent": True,
        }
    return {
        "keyboard": [
            [{"text": "➕ Жаңа презентация жасау"}],
            [{"text": "📂 Менің жобаларым"}, {"text": "💳 Баланс / Тарифтер"}],
            [{"text": "🎨 Дизайн таңдау"}, {"text": "📐 Үлгілер (Шаблон)"}],
            [{"text": "👥 Реферал (Табыс табу)"}, {"text": "🌐 Тіл / Язык"}],
            [{"text": "👨‍💻 Админмен байланыс"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }
