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
from io import StringIO

load_dotenv()
print("🔍 BOT_TOKEN:", os.getenv("BOT_TOKEN"))

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
json_str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
if not json_str:
    raise Exception("❌ Змінна GOOGLE_SHEETS_CREDENTIALS_JSON не знайдена!")
creds_dict = json.loads(json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(creds)

spreadsheet_id = '1pJU_6N3zyhRCdVfCPXD5RvHAvwVp0v71rKpvhpS3PC8'
sheet = gs_client.open_by_key(spreadsheet_id).worksheet("Лист1")
data = sheet.get_all_records()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Пошук🔍"), KeyboardButton(text="Список серіалів📺"), KeyboardButton(text="За жанром")],
        [KeyboardButton(text="Мультики👧"), KeyboardButton(text="Фільми")],
        [KeyboardButton(text="Запросити друга🥜🥛")]
    ],
    resize_keyboard=True
)

API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GROUP_CHAT_ID = '-1002649275599'
GROUP_URL = 'https://t.me/KinoTochkaUA'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

subscribe_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔔 Підписатися на групу", url=GROUP_URL)]
])

async def check_subscription(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(GROUP_CHAT_ID, user_id)
        logging.info(f"🔍 get_chat_member result: {chat_member}")
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"❌ Помилка перевірки підписки: {e}")
        return False

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        if isinstance(event, types.Message):
            if event.text and any(cmd in event.text.lower() for cmd in ["/my_status", "/get_chat_id"]):
                return await handler(event, data)
            if not await check_subscription(event.from_user.id):
                await event.reply("❌ Щоб користуватись ботом, підпишіться на групу:", reply_markup=subscribe_kb)
                return
        return await handler(event, data)

dp.message.middleware(SubscriptionMiddleware())

# Обробники залишаються як було...
# ...

@app.post("/webhook")
async def telegram_webhook(update: dict):
    telegram_update = Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "OK"}

@app.get("/ping")
async def ping():
    return {"status": "pong", "uptime": "working 🟢"}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"🔔 Webhook set to: {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    logging.info("🔔 Webhook deleted")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
