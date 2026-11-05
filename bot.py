import asyncio
import os
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from config import TELEGRAM_BOT_TOKEN
from services.llm_service import LLMService
from services.pptx_service import PPTXService

router = Router()

class PresentationStates(StatesGroup):
    waiting_for_topic = State()
    waiting_for_slide_count = State()
    waiting_for_images = State()
    waiting_for_language = State()
    waiting_for_style = State()
    confirm = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Презентация жасау", callback_data="start_creation")],
        [InlineKeyboardButton(text="📚 Менің презентацияларым", callback_data="my_presentations")],
        [InlineKeyboardButton(text="❓ Көмек", callback_data="help")]
    ])
    await message.answer(
        "Сәлем! 👋 Мен саған AI көмегімен әдемі презентация жасап беремін.\n"
        "Тақырыбыңды жаз — қалғанын бірге дайындаймыз!",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    await callback.message.answer(
        "❓ Көмек:\n"
        "Бұл бот арқылы кез келген тақырыпта кәсіби PPTX презентациясын, слайдтар жоспарын және ауызша қорғау мәтінін жасай аласыз.\n"
        "Бастау үшін «🎨 Презентация жасау» батырмасын басыңыз."
    )
    await callback.answer()

@router.callback_query(F.data == "start_creation")
async def callback_start_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PresentationStates.waiting_for_topic)
    await callback.message.answer("Қандай тақырыпқа презентация керек? Мысалы: Абай жолы, Қазақстан тарихы, Жасанды интеллект.")
    await callback.answer()

@router.message(PresentationStates.waiting_for_topic)
async def process_topic(message: Message, state: FSMContext):
    topic = message.text.strip()
    if len(topic) < 2:
        await message.answer("Тақырып тым қысқа. Нақтырақ жазыңызші:")
        return
    await state.update_data(topic=topic)
    await state.set_state(PresentationStates.waiting_for_slide_count)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 слайд", callback_data="slides_5"), InlineKeyboardButton(text="10 слайд", callback_data="slides_10")],
        [InlineKeyboardButton(text="15 слайд", callback_data="slides_15"), InlineKeyboardButton(text="20 слайд", callback_data="slides_20")],
        [InlineKeyboardButton(text="✍️ Өзім енгіземін", callback_data="slides_custom")]
    ])
    await message.answer("Презентация неше слайдтан тұрсын?", reply_markup=keyboard)

@router.callback_query(F.data.startswith("slides_"))
async def process_slide_count_callback(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "slides_custom":
        await callback.message.answer("Слайд санын санмен жазыңыз (мысалы: 12):")
        await callback.answer()
        return
    
    count = int(data.split("_")[1])
    await state.update_data(slide_count=count)
    await ask_images(callback.message, state)
    await callback.answer()

@router.message(PresentationStates.waiting_for_slide_count)
async def process_slide_count_text(message: Message, state: FSMContext):
    try:
        count = int(message.text.strip())
        if not (3 <= count <= 50):
            await message.answer("Слайд саны 3 пен 50 аралығында болуы тиіс. Қайта енгізіңіз:")
            return
        await state.update_data(slide_count=count)
        await ask_images(message, state)
    except ValueError:
        await message.answer("Тек сан енгізіңіз (мысалы: 15):")

async def ask_images(message: Message, state: FSMContext):
    await state.set_state(PresentationStates.waiting_for_images)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼️ Иә, суреттер керек", callback_data="img_yes")],
        [InlineKeyboardButton(text="📝 Жоқ, тек мәтін", callback_data="img_no")]
    ])
    await message.answer("Презентацияға суреттер қосайын ба?", reply_markup=keyboard)

@router.callback_query(F.data.startswith("img_"))
async def process_images(callback: CallbackQuery, state: FSMContext):
    need_images = (callback.data == "img_yes")
    await state.update_data(need_images=need_images)
    await state.set_state(PresentationStates.waiting_for_language)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kk"), InlineKeyboardButton(text="🇷🇺 Орысша", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 Ағылшынша", callback_data="lang_en")]
    ])
    await callback.message.answer("Қай тілде дайындайын?", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("lang_"))
async def process_language(callback: CallbackQuery, state: FSMContext):
    lang_map = {"lang_kk": "қазақша", "lang_ru": "орысша", "lang_en": "ағылшынша"}
    language = lang_map.get(callback.data, "қазақша")
    await state.update_data(language=language)
    await state.set_state(PresentationStates.waiting_for_style)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Академиялық", callback_data="style_academic"), InlineKeyboardButton(text="✨ Заманауи", callback_data="style_modern")],
        [InlineKeyboardButton(text="💼 Іскерлік", callback_data="style_business"), InlineKeyboardButton(text="🎨 Креативті", callback_data="style_creative")]
    ])
    await callback.message.answer("Дизайн стилін таңдаңыз:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("style_"))
async def process_style(callback: CallbackQuery, state: FSMContext):
    style_map = {
        "style_academic": "академиялық",
        "style_modern": "заманауи",
        "style_business": "іскерлік",
        "style_creative": "креативті"
    }
    style = style_map.get(callback.data, "академиялық")
    await state.update_data(style=style)
    await state.set_state(PresentationStates.confirm)
    
    data = await state.get_data()
    summary_text = (
        f"📌 Презентация параметрлері:\n"
        f"• Тақырып: {data.get('topic')}\n"
        f"• Слайд саны: {data.get('slide_count')}\n"
        f"• Суреттер: {'Иә' if data.get('need_images') else 'Жоқ'}\n"
        f"• Тіл: {data.get('language')}\n"
        f"• Дизайн: {style}\n\n"
        f"Бастаймыз ба?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☑ Презентация жасау", callback_data="generate_confirm")],
        [InlineKeyboardButton(text="❌ Болдырмау", callback_data="cancel")]
    ])
    await callback.message.answer(summary_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Презентация жасау тоқтатылды. Бастау үшін /start жіберіңіз.")
    await callback.answer()

@router.callback_query(F.data == "generate_confirm")
async def callback_generate(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    msg = await callback.message.answer("⏳ Тақырып талдануда...")
    
    try:
        topic = data.get("topic")
        slide_count = data.get("slide_count", 10)
        language = data.get("language", "қазақша")
        style = data.get("style", "академиялық")
        need_images = data.get("need_images", True)
        
        await asyncio.sleep(1)
        await msg.edit_text("📝 Слайдтар мен мазмұн жасалуда (AI)...")
        
        presentation_data = await LLMService.generate_presentation_structure(topic, slide_count, language, style)
        
        await asyncio.sleep(1)
        await msg.edit_text("🖼️ Суреттер таңдалып, дизайн құрастырылуда...")
        
        os.makedirs("temp", exist_ok=True)
        file_path = f"temp/{callback.from_user.id}_{int(asyncio.get_event_loop().time())}.pptx"
        PPTXService.create_presentation(presentation_data, file_path, need_images=need_images)
        
        await asyncio.sleep(1)
        await msg.edit_text("📦 Файл дайын! Жіберілуде...")
        
        pptx_file = FSInputFile(file_path)
        await callback.message.answer_document(pptx_file, caption=f"🎉 Сіздің презентацияңыз дайын: {topic}")
        
        plan_summary = presentation_data.get("plan_summary", [])
        if plan_summary:
            plan_text = "📖 Презентация жоспары:\n\n" + "\n".join(plan_summary)
            if len(plan_text) > 4000:
                plan_text = plan_text[:4000] + "\n..."
            await callback.message.answer(plan_text)
            
        speech_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗣️ Ауызша қорғау мәтінін алу", callback_data=f"speech")]
        ])
        await callback.message.answer("Әр слайдты ауызша қорғауға арналған мәтінді алғыңыз келсе, батырманы басыңыз:", reply_markup=speech_keyboard)
        
    except Exception as e:
        logger.error(f"Generation error: {e}")
        await msg.edit_text("❌ Кешіріңіз, презентация жасау кезінде қате орын алды. Кейінірек қайталап көріңіз.")
    await callback.answer()

@router.callback_query(F.data == "speech")
async def callback_speech(callback: CallbackQuery):
    await callback.message.answer("🗣️ Қорғауға арналған жалпы кеңес:\nӘр слайдты қорғағанда негізгі тезистерді ашып айтыңыз, ұзын мәтіндерді оқымай, аудиториямен көзбен байланыс орнатыңыз.")
    await callback.answer()

async def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN табылмады!")
        return
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    logger.info("Бот іске қосылды...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
