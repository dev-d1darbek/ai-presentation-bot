"""
Persistent reply keyboard for Telegram Bot (Trilingual: kk / ru / en).
Admin button is shown ONLY when is_admin_user=True.
"""
from typing import Dict, Any, List
from app.bot.i18n import t, norm_lang


def get_persistent_reply_keyboard(ui_lang: str = "kk", is_admin_user: bool = False) -> Dict[str, Any]:
    """Returns persistent bottom reply keyboard dictionary in kk, ru, or en."""
    l = norm_lang(ui_lang)
    rows: List[List[Dict[str, str]]] = [
        [{"text": t("btn_new", l)}],
        [{"text": t("btn_projects", l)}, {"text": t("btn_lang", l)}],
        [{"text": t("btn_balance", l)}, {"text": t("btn_support", l)}],
    ]
    if is_admin_user:
        rows.append([{"text": t("btn_admin", l)}])
    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "is_persistent": True,
    }
