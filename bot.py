import os
import json
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = "8048162931:AAFr4yGELPzIDo9Tpf6WtMORXIC2efvaT-Y"

if not BOT_TOKEN:
    logging.error("❌ Токен не найден в .env файле!")
    exit(1)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Глобальная переменная для данных квеста
QUEST_DATA = {}

# Загрузка квеста
def load_quest():
    global QUEST_DATA
    try:
        with open("quest_data.json", "r", encoding="utf-8") as f:
            QUEST_DATA = json.load(f)
        logging.info("✅ Квест успешно загружен!")
        return True
    except FileNotFoundError:
        logging.error("❌ Файл quest_data.json не найден!")
        return False
    except json.JSONDecodeError as e:
        logging.error(f"❌ Ошибка в JSON: строка {e.lineno}, столбец {e.colno}")
        return False

class GameState(StatesGroup):
    playing = State()

@dp.message(CommandStart())
async def start_game(message: types.Message, state: FSMContext):
    if not QUEST_DATA:
        await message.answer("❌ Ошибка загрузки квеста. Обратитесь к разработчику.")
        return
    
    await state.set_state(GameState.playing)
    await state.update_data(current_scene="start")
    await send_scene(message.chat.id, state)

async def send_scene(chat_id: int, state: FSMContext):
    data = await state.get_data()
    scene_id = data.get("current_scene", "start")
    
    if scene_id not in QUEST_DATA:
        await bot.send_message(chat_id, f"❌ Сцена '{scene_id}' не найдена. Начинаем сначала.")
        scene_id = "start"
    
    scene = QUEST_DATA[scene_id]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    
    # Создаем кнопки
    for option in scene.get("options", []):
        keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(
                text=option["text"],
                callback_data=option["next_scene"]
            )
        ])
    
    # Отправляем изображение + текст
    try:
        # Если есть изображение в сцене
        if "image" in scene and scene["image"].strip():
            logging.info(f"🖼️ Отправка изображения: {scene['image']}")
            # Отправляем фото с текстом под ним
            await bot.send_photo(
                chat_id=chat_id,
                photo=scene["image"],
                caption=scene["text"],
                reply_markup=keyboard
            )
        else:
            # Если изображения нет - отправляем обычный текст
            await bot.send_message(
                chat_id=chat_id,
                text=scene["text"],
                reply_markup=keyboard
            )
    except TelegramAPIError as e:
        logging.error(f"❌ Ошибка Telegram API: {e}")
        # Резервный вариант без изображения
        await bot.send_message(
            chat_id=chat_id,
            text=f"🖼️ {scene['text']}\n\n(Изображение не загрузилось)",
            reply_markup=keyboard
        )

@dp.callback_query(F.data, GameState.playing)
async def handle_choice(callback: types.CallbackQuery, state: FSMContext):
    next_scene = callback.data
    
    if next_scene not in QUEST_DATA:
        await callback.answer("❌ Эта сцена находится в разработке!", show_alert=True)
        return
    
    await state.update_data(current_scene=next_scene)
    await callback.answer()
    await send_scene(callback.message.chat.id, state)

@dp.message()
async def fallback(message: types.Message):
    await message.answer("🎮 Начните игру командой /start")

if __name__ == "__main__":
    if load_quest():
        logging.info("🚀 Бот запускается с поддержкой изображений...")
        dp.run_polling(bot)
    else:
        logging.error("🛑 Запуск отменён из-за ошибок в квесте.")