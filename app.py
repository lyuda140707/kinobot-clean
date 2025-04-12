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
from aiogram.types import Update

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
        [KeyboardButton(text="Запросити друга🦜🦛")]
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

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    logging.info(f"👋 /start від @{message.from_user.username} ({message.from_user.id})")
    if await check_subscription(message.from_user.id):
        await message.answer("✅ Ви підписані! Ласкаво просимо до бота!\nОбирай жанр, або натисни «Меню» 👇", reply_markup=main_menu)
    else:
        await message.answer("❌ Щоб користуватись ботом, підпишіться на групу:", reply_markup=subscribe_kb)

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer("❓ Натисніть /menu, щоб побачити всі доступні функції.", reply_markup=main_menu)

@dp.message(Command("id"))
async def get_id(message: types.Message):
    await message.answer(f"Ваш Telegram ID: {message.from_user.id}")

@dp.message(Command("my_status"))
async def my_status(message: types.Message):
    try:
        chat_member = await bot.get_chat_member(GROUP_CHAT_ID, message.from_user.id)
        await message.answer(f"📋 Ваш статус у групі: {chat_member.status}")
    except Exception as e:
        await message.answer(f"❌ Помилка перевірки: {e}")

@dp.message(F.text == "Меню")
@dp.message(Command("menu"))
async def menu_handler(message: types.Message):
    await message.answer("Ось ваше меню:", reply_markup=main_menu)

@dp.message(F.text == "Пошук🔍")
@dp.message(Command("poisk"))
async def prompt_search(message: types.Message):
    logging.info(f"🔍 Користувач {message.from_user.id} натиснув кнопку 'Пошук'")
    await message.answer("🔎 Введіть назву фільму або серіалу для пошуку:")

@dp.message(F.text == "Список серіалів")
@dp.message(Command("serialiv"))
async def serials_handler(message: types.Message):
    await message.reply("Список серіалів.")

@dp.message(F.text == "За жанром")
@dp.message(Command("zhanrom"))
async def genres_handler(message: types.Message):
    await message.reply("Серіали за жанром.")

@dp.message(F.text == "Мультики")
@dp.message(Command("multik"))
async def cartoons_handler(message: types.Message):
    await message.reply("Мультики.")

@dp.message(F.text == "Фільми")
@dp.message(Command("filmi"))
async def movies_handler(message: types.Message):
    await message.reply("Фільми.")

@dp.message(F.text == "Запросити друга")
@dp.message(Command("zaprosy"))
async def invite_handler(message: types.Message):
    await message.reply("Запросіть друга за цим посиланням...")

@dp.message(F.text == "Перегляд")
@dp.message(Command("pereglyad"))
async def view_handler(message: types.Message):
    await message.reply("📺 Перегляд серіалів.")

@dp.message()
async def universal_handler(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Щоб користуватись ботом, підпишіться на групу:", reply_markup=subscribe_kb)
        return

    query = message.text.strip().lower()
    logging.info(f"🔎 Користувач @{message.from_user.username} ({message.from_user.id}) шукає: {query}")
    results = []

    query = message.text.strip().lower()
    results = []
    for row in data:
        title = row.get("Назва", "").lower()
        description = row.get("Опис", "")
        link = row.get("Посилання", "")
        if query in title:
            results.append(f"🎬 *{row.get('Назва')}*\n📝 {description}\n🔗 [Дивитись]({link})")

    if results:
        await message.answer("\n\n".join(results), parse_mode="Markdown")
    else:
        await message.answer("❌ Нічого не знайдено. Спробуйте інший запит.")

@app.post("/sendpulse-webhook")
async def sendpulse_webhook_handler(request: Request):
    try:
        data = await request.json()
        logging.info(f"SendPulse webhook: {data}")
        telegram_id = None
        if isinstance(data, list) and data:
            telegram_id = data[0].get("telegram_id")
        elif isinstance(data, dict):
            telegram_id = data.get("telegram_id")
        is_subscribed = False
        if telegram_id:
            is_subscribed = await check_subscription(int(telegram_id))
        return JSONResponse(content={"allowed": is_subscribed})
    except Exception as e:
        logging.error(f"SendPulse error: {e}")
        return JSONResponse(content={"allowed": False})

@dp.message(Command("get_chat_id"))
async def get_chat_id(message: types.Message):
    await message.answer(
        f"🆔 Chat ID: `{message.chat.id}`\n📌 Тип: {message.chat.type}\n📛 Назва: {message.chat.title}",
        parse_mode="Markdown"
    )

@app.get("/")
async def root():
    return {"status": "OK"}

@app.post("/")
async def telegram_webhook(update: dict):
    telegram_update = Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

@app.get("/ping")
async def ping():
    return {"status": "pong", "uptime": "working 🟢"}
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
