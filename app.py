import os
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Callable, Dict, Any, Awaitable
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import TelegramObject, InlineKeyboardMarkup, InlineKeyboardButton, Update, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# 🌐 Load env vars
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # must NOT end with "/webhook"
GROUP_CHAT_ID = '-1002649275599'
GROUP_URL = 'https://t.me/KinoTochkaUA'

# 🚀 Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🚀 Google Sheets creds
json_str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
if not json_str:
    raise Exception("❌ GOOGLE_SHEETS_CREDENTIALS_JSON not found")
creds_dict = json.loads(json_str)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_key('1pJU_6N3zyhRCdVfCPXD5RvHAvwVp0v71rKpvhpS3PC8').worksheet("Лист1")
data = sheet.get_all_records()

# 🚀 FastAPI & Aiogram
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

# 🔐 Subscribe check
subscribe_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔔 Підписатися", url=GROUP_URL)]])

async def check_subscription(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(GROUP_CHAT_ID, user_id)
        logging.info(f"🔍 {user_id} status: {chat_member.status}")
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"❌ Subscription check failed: {e}")
        return False

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        if isinstance(event, types.Message):
            if event.text and any(cmd in event.text.lower() for cmd in ["/my_status", "/get_chat_id"]):
                return await handler(event, data)
            if not await check_subscription(event.from_user.id):
                await event.reply("❌ Спершу підпишіться на канал", reply_markup=subscribe_kb)
                return
        return await handler(event, data)

# Меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Пошук🔍"), KeyboardButton(text="Список серіалів📺"), KeyboardButton(text="За жанром")],
        [KeyboardButton(text="Мультики👧"), KeyboardButton(text="Фільми")],
        [KeyboardButton(text="Запросити друга🍜🍻")]
    ],
    resize_keyboard=True
)

# Middleware реєстрація
dp.message.middleware(SubscriptionMiddleware())

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if await check_subscription(message.from_user.id):
        await message.answer("Ласкаво просимо!", reply_markup=main_menu)
    else:
        await message.answer("❌ Підпишись!", reply_markup=subscribe_kb)

@dp.message(F.text == "Пошук🔍")
async def search_prompt(message: types.Message):
    await message.answer("🔎 Введіть назву...")

@dp.message()
async def search_logic(message: types.Message):
    if not await check_subscription(message.from_user.id):
        return await message.answer("❌ Спершу підпишись!", reply_markup=subscribe_kb)

    query = message.text.strip().lower()
    logging.info(f"🔍 Користувач @{message.from_user.username} шукає: {query}")

    matches = []
    for row in data:
        name = row.get("Назва", "").lower()
        description = row.get("Опис", "")
        link = row.get("Посилання", "")
        if query in name:
            matches.append(f"🎬 *{row.get('Назва')}*\n📝 {description}\n🔗 [Дивитись]({link})")

    if matches:
        await message.answer("\n\n".join(matches), parse_mode="Markdown")
    else:
        await message.answer("❌ Нічого не знайдено")
        
@app.post("/webhook")
async def telegram_webhook(update: dict):
    logging.info("✅ Webhook endpoint отримав update!")
    logging.info("📩 Вхідний update: %s", update)

    telegram_update = Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}

@app.on_event("startup")
async def on_start():
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook встановлено: {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_stop():
    await bot.delete_webhook()
    logging.info("❌ Webhook видалено")

@app.get("/")
async def root():
    return {"status": "working"}

@app.get("/ping")
async def ping():
    return {"status": "pong"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
