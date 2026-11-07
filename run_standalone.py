"""
Standalone Async Telegram Bot Runner.
Uses httpx directly to poll Telegram Bot API without framework dependencies.
Includes Modern UI/UX, PDF/PPTX Dual Export, and Admin Statistics.
"""
import asyncio
import logging
import re
from typing import Optional, Dict, Any
import httpx

import config
from app.core.themes import detect_best_theme_for_topic, THEMES_REGISTRY, get_selected_theme_label
from app.core.db import log_user, get_all_user_ids
from app.bot.session import get_telegram_session
from app.bot.keyboards.reply import get_persistent_reply_keyboard
from app.bot.keyboards.inline import (
    build_topic_ready_text,
    build_topic_ready_keyboard,
    build_clean_themes_keyboard,
    build_default_slides_keyboard,
    build_post_generation_keyboard,
    build_admin_keyboard,
)
from app.bot.service import (
    parse_user_input,
    generate_deck_for_session,
    build_pdf_for_session,
    reexport_deck_with_theme,
    format_admin_dashboard_text,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class TelegramAPIClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

    async def send_message(self, chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None, parse_mode: str = "HTML") -> Optional[int]:
        payload: Dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(f"{self.base_url}/sendMessage", json=payload)
                data = res.json()
                return data.get("result", {}).get("message_id")
        except Exception as e:
            logger.error(f"send_message error: {e}")
        return None

    async def edit_message(self, chat_id: int, message_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None, parse_mode: str = "HTML"):
        payload: Dict[str, Any] = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(f"{self.base_url}/editMessageText", json=payload)
        except Exception:
            pass

    async def delete_message(self, chat_id: int, message_id: int):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(f"{self.base_url}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
        except Exception:
            pass

    async def send_chat_action(self, chat_id: int, action: str = "upload_document"):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(f"{self.base_url}/sendChatAction", json={"chat_id": chat_id, "action": action})
        except Exception:
            pass

    async def answer_callback(self, callback_query_id: str, text: Optional[str] = None, show_alert: bool = False):
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            payload["text"] = text
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(f"{self.base_url}/answerCallbackQuery", json=payload)
        except Exception:
            pass

    async def send_document(
        self,
        chat_id: int,
        document_bytes: bytes,
        filename: str,
        caption: str,
        mime_type: str = "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = "HTML"
    ) -> bool:
        try:
            files = {"document": (filename, document_bytes, mime_type)}
            data = {"chat_id": str(chat_id), "caption": caption, "parse_mode": parse_mode}
            if reply_markup:
                import json
                data["reply_markup"] = json.dumps(reply_markup)

            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.base_url}/sendDocument", data=data, files=files)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"send_document error: {e}")
            return False

async def handle_generation_workflow(
    tg: TelegramAPIClient,
    chat_id: int,
    session,
    user_id: Optional[int] = None,
    slide_count: Optional[int] = None,
    existing_msg_id: Optional[int] = None
):
    topic = session.pendingTopic or (session.lastPresentation.topic if session.lastPresentation else "Жасанды интеллект")
    count = slide_count or session.slideCount
    selected_theme = (
        THEMES_REGISTRY[session.designId]
        if session.designId != "auto" and session.designId in THEMES_REGISTRY
        else detect_best_theme_for_topic(topic)
    )

    status_text = (
        f"⏳ «{topic}» презентациясы дайындалуда...\n\n"
        f"📄 Бет саны: {count} слайд\n"
        f"🎨 Дизайн: {selected_theme.nameKz}\n\n"
        f"Күте тұрыңыз, дайын файл бірнеше секундта жіберіледі..."
    )

    status_msg_id = None
    if existing_msg_id:
        await tg.edit_message(chat_id, existing_msg_id, status_text)
        status_msg_id = existing_msg_id
    else:
        status_msg_id = await tg.send_message(chat_id, status_text)

    await tg.send_chat_action(chat_id, "upload_document")

    try:
        pptx_bytes, filename, presentation = await generate_deck_for_session(session, user_id=user_id or chat_id, slide_count=count)
        caption = (
            f"✅ <b>Презентация дайын!</b>\n"
            f"📌 Тақырып: {topic}\n"
            f"📄 Бет саны: {presentation.slide_count} слайд\n"
            f"🎨 Дизайн: {selected_theme.nameKz}\n\n"
            f"👇 PDF форматында жүктеу немесе дизайнды ауыстыру:"
        )
        await tg.send_document(
            chat_id,
            pptx_bytes,
            filename,
            caption,
            reply_markup=build_post_generation_keyboard(has_pdf=False)
        )
        if status_msg_id:
            await tg.delete_message(chat_id, status_msg_id)
    except Exception as e:
        logger.error(f"Generation error: {e}")
        await tg.send_message(
            chat_id,
            "❌ Кешіріңіз, презентация жасау барысында қате орын алды. Тақырыпты қайта жазып көріңіз."
        )

async def handle_update(tg: TelegramAPIClient, update: Dict[str, Any]):
    # 1. Inline Buttons (callback_query)
    if "callback_query" in update:
        cq = update["callback_query"]
        cq_id = cq.get("id")
        msg = cq.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        msg_id = msg.get("message_id")
        from_user = cq.get("from", {})
        user_id = from_user.get("id")
        is_doc = bool(msg.get("document"))
        data = str(cq.get("data", ""))

        if not chat_id:
            return
        session = get_telegram_session(chat_id)

        if data == "noop":
            await tg.answer_callback(cq_id)
            return

        # Export PDF
        if data == "export_pdf":
            if not session.lastPresentation:
                await tg.answer_callback(cq_id, "Алдымен презентация жасаңыз.", show_alert=True)
                return

            await tg.answer_callback(cq_id, "📑 PDF форматы дайындалуда...")
            await tg.send_chat_action(chat_id, "upload_document")

            pdf_res = build_pdf_for_session(session)
            if not pdf_res:
                await tg.send_message(chat_id, "❌ PDF жасауда қате орын алды.")
                return

            pdf_bytes, filename = pdf_res
            caption = (
                f"📑 <b>PDF форматындағы презентация дайын!</b>\n"
                f"📌 Тақырып: {session.lastPresentation.topic}\n"
                f"📄 Бет саны: {session.lastPresentation.slide_count} слайд"
            )
            await tg.send_document(
                chat_id,
                pdf_bytes,
                filename,
                caption,
                mime_type="application/pdf",
                reply_markup=build_post_generation_keyboard(has_pdf=True)
            )
            return

        # Export PPTX
        if data == "export_pptx":
            if not session.lastPresentation:
                await tg.answer_callback(cq_id, "Алдымен презентация жасаңыз.", show_alert=True)
                return

            from app.pptx_generator.engine import build_pptx_deck
            await tg.answer_callback(cq_id, "📥 PPTX дайындалуда...")
            await tg.send_chat_action(chat_id, "upload_document")
            pptx_bytes = build_pptx_deck(session.lastPresentation)
            base_name = re.sub(r'[^a-zA-Z0-9\u0400-\u04FF]', '_', session.lastPresentation.topic)[:40].strip('_') or "presentation"
            caption = (
                f"✅ <b>PPTX презентация дайын!</b>\n"
                f"📌 Тақырып: {session.lastPresentation.topic}\n"
                f"📄 Бет саны: {session.lastPresentation.slide_count} слайд"
            )
            await tg.send_document(
                chat_id,
                pptx_bytes,
                f"{base_name}.pptx",
                caption,
                reply_markup=build_post_generation_keyboard(has_pdf=False)
            )
            return

        # Admin refresh
        if data == "admin_refresh":
            if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
                await tg.answer_callback(cq_id, "Рұқсат жоқ", show_alert=True)
                return
            await tg.edit_message(chat_id, msg_id, format_admin_dashboard_text(), build_admin_keyboard())
            await tg.answer_callback(cq_id, "Жаңартылды!")
            return

        if data.startswith("gen_now:"):
            n = int(data.split(":")[1])
            session.slideCount = n
            await tg.answer_callback(cq_id, f"🚀 {n} беттік презентация жасалуда...")
            await handle_generation_workflow(tg, chat_id, session, user_id=user_id, slide_count=n, existing_msg_id=msg_id if not is_doc else None)
            return

        if data.startswith("save_default_slides:"):
            n = int(data.split(":")[1])
            session.slideCount = n
            await tg.answer_callback(cq_id, f"✅ Әдепкі бет саны: {n} бет")
            if session.pendingTopic:
                text = build_topic_ready_text(session)
                kb = build_topic_ready_keyboard(session)
                if msg_id and not is_doc:
                    await tg.edit_message(chat_id, msg_id, text, kb)
                else:
                    await tg.send_message(chat_id, text, kb)
            elif msg_id and not is_doc:
                await tg.edit_message(
                    chat_id,
                    msg_id,
                    f"✅ Әдепкі бет саны {n} слайд болып сақталды.\n\nЕнді кез келген презентация тақырыбын жазыңыз!"
                )
            return

        if data == "open_slides_regen":
            await tg.answer_callback(cq_id)
            topic = session.pendingTopic or (session.lastPresentation.topic if session.lastPresentation else "Презентация")
            await tg.send_message(
                chat_id,
                f"📄 «{topic}» презентациясын неше бетпен қайта жасаймыз?\nБатырманы бассаңыз, бірден дайындалады:",
                build_default_slides_keyboard(session, is_regenerate=True)
            )
            return

        if data.startswith("open_themes:"):
            parts = data.split(":")
            page = int(parts[1]) if len(parts) > 1 else 0
            mode = parts[2] if len(parts) > 2 else "default"
            session.themePage = page
            await tg.answer_callback(cq_id)

            text = (
                "🎨 Жаңа дизайнды бассаңыз, дайын файл бірден сол дизайнмен қайта жіберіледі:"
                if mode == "reexport"
                else f"🎨 30 кәсіби дизайн ішінен ұнағанын таңдаңыз\n(Қазіргі: {get_selected_theme_label(session.designId, session.pendingTopic)}):"
            )
            kb = build_clean_themes_keyboard(session, page, mode)
            if msg_id and not is_doc:
                await tg.edit_message(chat_id, msg_id, text, kb)
            else:
                await tg.send_message(chat_id, text, kb)
            return

        if data.startswith("pick_theme:"):
            theme_id = data.split(":")[1]
            session.designId = theme_id
            label = get_selected_theme_label(theme_id, session.pendingTopic)
            await tg.answer_callback(cq_id, f"✅ Таңдалды: {label}")

            if session.pendingTopic:
                text = build_topic_ready_text(session)
                kb = build_topic_ready_keyboard(session)
                if msg_id and not is_doc:
                    await tg.edit_message(chat_id, msg_id, text, kb)
                else:
                    await tg.send_message(chat_id, text, kb)
            elif msg_id and not is_doc:
                await tg.edit_message(
                    chat_id,
                    msg_id,
                    f"✅ Дизайн сақталды: {label}\n📄 Бет саны: {session.slideCount} бет\n\nЕнді презентация тақырыбын жазыңыз!"
                )
            return

        if data.startswith("reexport_theme:"):
            theme_id = data.split(":")[1]
            session.designId = theme_id
            if not session.lastPresentation:
                await tg.answer_callback(cq_id, "Алдымен тақырып жазып презентация жасап алыңыз.", show_alert=True)
                return

            res = reexport_deck_with_theme(session, theme_id)
            if not res:
                await tg.answer_callback(cq_id, "Қате орын алды.")
                return

            pptx_bytes, filename, theme_name_kz = res
            await tg.answer_callback(cq_id, f"🎨 «{theme_name_kz}» дизайнымен жіберілуде...")
            await tg.send_chat_action(chat_id, "upload_document")

            caption = (
                f"🎨 <b>Жаңа дизайнмен дайын!</b>\n"
                f"📌 Тақырып: {session.lastPresentation.topic}\n"
                f"📄 Бет саны: {session.lastPresentation.slide_count} слайд\n"
                f"🎨 Дизайн: {theme_name_kz}\n\n"
                f"👇 PDF нұсқасын жүктеу немесе басқа стиль таңдау:"
            )
            await tg.send_document(
                chat_id,
                pptx_bytes,
                filename,
                caption,
                reply_markup=build_post_generation_keyboard(has_pdf=False)
            )
            return

        if data == "back_to_topic":
            await tg.answer_callback(cq_id)
            text = build_topic_ready_text(session)
            kb = build_topic_ready_keyboard(session)
            if msg_id and not is_doc:
                await tg.edit_message(chat_id, msg_id, text, kb)
            else:
                await tg.send_message(chat_id, text, kb)
            return

    # 2. Text Messages
    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        text = (msg.get("text") or "").strip()
        from_user = msg.get("from", {})
        user_id = from_user.get("id")
        if not chat_id or not text:
            return

        log_user(user_id, from_user.get("username"), from_user.get("first_name"))
        session = get_telegram_session(chat_id)

        if text == "/start":
            welcome = (
                f"👋 Сәлем! Мен кәсіби AI Presentation Bot-пын.\n\n"
                f"Кез келген презентация тақырыбын жаза салыңыз (мысалы: «Жасанды интеллект» немесе «Қазақстан тарихы 10 бет»).\n\n"
                f"⚙️ Қазіргі баптаулар:\n"
                f"• Бет саны: {session.slideCount} слайд\n"
                f"• Дизайн: {get_selected_theme_label(session.designId)}"
            )
            await tg.send_message(chat_id, welcome, get_persistent_reply_keyboard())
            return

        if text == "/admin":
            if config.ADMIN_IDS and user_id not in config.ADMIN_IDS:
                await tg.send_message(chat_id, "⛔️ Бұл команда тек бот әкімшісіне арналған.")
                return
            dashboard = format_admin_dashboard_text()
            if not config.ADMIN_IDS:
                dashboard += f"\n\n💡 <i>Кеңес: Өз Telegram ID-іңізді (<code>{user_id}</code>) .env файлына ADMIN_IDS={user_id} деп жазып қойыңыз.</i>"
            await tg.send_message(chat_id, dashboard, build_admin_keyboard())
            return

        if text in ("/slides", "📄 Бет саны", "📄 Бет санын таңдау"):
            await tg.send_message(
                chat_id,
                f"📄 Неше беттік презентация жасағыңыз келеді? (Қазір: {session.slideCount} бет):",
                build_default_slides_keyboard(session, is_regenerate=False)
            )
            return

        if text in ("/design", "🎨 Дизайн таңдау", "🎨 Дизайн таңдау (30 стиль)"):
            mode = "topic" if session.pendingTopic else "default"
            await tg.send_message(
                chat_id,
                f"🎨 30 кәсіби дизайн шаблонынан таңдаңыз (Қазір: {get_selected_theme_label(session.designId, session.pendingTopic)}):",
                build_clean_themes_keyboard(session, session.themePage, mode)
            )
            return

        if text in ("/help", "❓ Көмек", "/settings", "⚙️ Ағымдағы баптаулар"):
            help_text = (
                "ℹ️ Қолдану өте оңай:\n\n"
                "1. Чатқа презентация тақырыбын жазыңыз (мысалы: «Жасанды интеллект»).\n"
                "2. Шыққан терезеден бет санын бассаңыз (8, 10, 12, 15, 20), бот дайын .PPTX және .PDF файлын береді!\n"
                "3. Файл астындағы «🎨 Дизайнын ауыстыру» арқылы 30 стильдің кез келгеніне 1 секундта ауыстыра аласыз."
            )
            await tg.send_message(chat_id, help_text, get_persistent_reply_keyboard())
            return

        # Slide count only
        only_slide_match = re.match(r'^(\d{1,2})\s*(бет|слайд|беттік|слайдтан)(\s+болсын|\s+жаса|\s+қыл)?$', text, re.IGNORECASE)
        if only_slide_match:
            num = max(config.MIN_SLIDE_COUNT, min(int(only_slide_match.group(1)), config.MAX_SLIDE_COUNT))
            session.slideCount = num
            if session.pendingTopic or session.lastPresentation:
                await handle_generation_workflow(tg, chat_id, session, user_id=user_id)
            else:
                await tg.send_message(
                    chat_id,
                    f"✅ Бет саны {num} слайд болып белгіленді. Енді презентация тақырыбын жазыңыз!",
                    get_persistent_reply_keyboard()
                )
            return

        # Extract topic, inline count, theme mention
        clean_topic, inline_count, theme_mention = parse_user_input(text)
        if inline_count:
            session.slideCount = inline_count
        if theme_mention:
            session.designId = theme_mention

        session.pendingTopic = clean_topic

        # Direct generation if inline count was provided
        if inline_count:
            await handle_generation_workflow(tg, chat_id, session, user_id=user_id)
            return

        # Otherwise show 1-tap card
        await tg.send_message(
            chat_id,
            build_topic_ready_text(session),
            build_topic_ready_keyboard(session)
        )

async def main():
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment or .env file!")
        return

    tg = TelegramAPIClient(token)
    logger.info("🤖 AI Presentation Telegram Bot starting (Standalone Runner)...")

    offset = 0
    while True:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.get(f"{tg.base_url}/getUpdates?offset={offset}&timeout=20")
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok") and isinstance(data.get("result"), list):
                        for update in data["result"]:
                            offset = update["update_id"] + 1
                            asyncio.create_task(handle_update(tg, update))
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Polling error: {e}. Retrying in 3 seconds...")
            await asyncio.sleep(3.0)

if __name__ == "__main__":
    asyncio.run(main())
