import os
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Callable, Dict, Any, Awaitable
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import TelegramObject, InlineKeyboardMarkup, InlineKeyboardButton, Update, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from collections import defaultdict
from urllib.parse import urlparse
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router
import asyncio

# 🌐 Load env vars
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
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
def parse_telegram_link(link):
    try:
        parts = urlparse(link)
        path_parts = parts.path.strip("/").split("/")
        if len(path_parts) != 2:
            return None, None
        chat_username = f"@{path_parts[0]}"
        message_id = int(path_parts[1])
        return chat_username, message_id
    except Exception as e:
        logging.error(f"❌ Не вдалося розібрати посилання: {e}")
        return None, None


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Пошук🔎"), KeyboardButton(text="Список серіалів📺"), KeyboardButton(text="За жанром")],
        [KeyboardButton(text="Мультики👧"), KeyboardButton(text="Фільми"), KeyboardButton(text="📅 Новинки")],
        [KeyboardButton(text="Запросити друга🤜🤛")]
    ],
    resize_keyboard=True
)


async def send_video_from_link(chat_id: int, link: str):
    try:
        # 1. Витягаємо username і message_id з посилання
        parts = link.strip().split("/")
        username = parts[3]
        msg_id = int(parts[4])

        # 2. Отримуємо реальний chat_id по username
        chat = await bot.get_chat(f"@{username}")
        real_chat_id = chat.id

        # 3. Отримуємо повідомлення
        msg = await bot.get_message(chat_id=real_chat_id, message_id=msg_id)
        if not msg.video:
            return await bot.send_message(chat_id, "⚠️ Це не відео")

        # 4. Надсилаємо відео без каналу
        await bot.send_video(chat_id, video=msg.video.file_id, caption=msg.caption or "")
    
    except Exception as e:
        logging.error(f"❌ Помилка при відправці відео: {e}")
        await bot.send_message(chat_id, f"❌ Не вдалося надіслати відео")
        
async def show_new_releases_effect(message: types.Message):
    await message.answer("🔍 Шукаю новинки...")
    await asyncio.sleep(1)
    await message.answer("🧠 Аналізую базу...")
    await asyncio.sleep(1)
    await message.answer("🎬 Знайдено! Обирай:")
    await asyncio.sleep(1)

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    logging.info(f"👋 /start від @{message.from_user.username} ({message.from_user.id})")

    if await check_subscription(message.from_user.id):
        await message.answer(
            "👋 Привіт! Це бот *«КіноТочка»* 🎬\nОбирай жанр, або натисни «Меню» 👇",
            reply_markup=main_menu,
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❌ Упс! Ви ще не з нами...\n\nЩоб користуватись ботом, будь ласка, *спершу підпишіться* на наш Telegram-канал 👇",
            reply_markup=subscribe_kb,
            parse_mode="Markdown"
        )

# Спільне повідомлення для перевірки
subscribe_text = (
    "❌ Упс! Ви ще не з нами 😢\n\n"
    "Щоб користуватись усіма фішками бота — підпишіться на наш канал 🎬\n\n"
    "👇 Тицяй кнопку — і ласкаво просимо!"
)

@dp.message(F.text == "Пошук🔎")
async def search_prompt(message: types.Message):
    await message.answer("🔎 Введіть назву...")
    return

@dp.message(F.text == "Список серіалів📺")
async def serials_handler(message: types.Message): 
    return

@dp.message(F.text == "За жанром")
async def genres_handler(message: types.Message):
    return

@dp.message(F.text == "Мультики👧")
async def cartoons_handler(message: types.Message):
    return
    

@dp.message(F.text == "Фільми")
async def movies_handler(message: types.Message):
    return

@dp.message(F.text == "Запросити друга🤜🤛")
async def invite_handler(message: types.Message):
    await message.answer("🐒 Поділись ботом з другом: https://t.me/KinoTochka24_bot")
    return
    
@dp.message(F.text == "📅 Новинки")
async def new_releases_handler(message: types.Message):
    if not await check_subscription(message.from_user.id):
        return await message.answer(subscribe_text, reply_markup=subscribe_kb)

    await show_new_releases_effect(message)  # 👈 Додано ефект очікування
    recent = data[-5:]  # Останні 5 записів
    grouped = defaultdict(list)
    for row in recent:
        grouped[row["Назва"]].append(row)

    for title, items in grouped.items():
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=item["Серія"], callback_data=f"send_video|{item['Посилання']}")]
            for item in items
        ])
        await message.answer(f"🆕 *{title}*\nОбери серію:", reply_markup=kb, parse_mode="Markdown")



from urllib.parse import urlparse


@dp.message()
async def search_logic(message: types.Message):
    skip_texts = ["Пошук🔍", "Список серіалів📽", "За жанром", "Мультики👧", "Фільми", "Запросити друга🤜🤛", "📅 Новинки"]

    if message.text in skip_texts:
        return

    if not await check_subscription(message.from_user.id):
        return await message.answer("❌ Спершу підпишись!", reply_markup=subscribe_kb)

    query = message.text.strip().lower()
    grouped = defaultdict(list)
    for row in data:
        title = row.get("Назва", "").strip()
        if query in title.lower():
            grouped[title].append(row)

    if not grouped:
        return await message.answer("❌ Нічого не знайдено")

    for title, items in grouped.items():
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=item["Серія"], callback_data=f"send_video|{item['Посилання']}")] for item in items
        ])
        await message.answer(f"🆕 *{title}*\nОбери серію:", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("send_video|"))
async def handle_video_callback(callback: types.CallbackQuery):
    await callback.answer()  # ⬅ Закриває "loading" у Telegram

    link = callback.data.split("|")[1]
    chat_username, message_id = parse_telegram_link(link)

    if not chat_username or not message_id:
        return await callback.message.answer("❌ Невірне посилання")

    try:
        await bot.copy_message(
            chat_id=callback.from_user.id,
            from_chat_id=chat_username,
            message_id=message_id
        )
    except Exception as e:
        logging.error(f"❌ Не вдалося переслати відео: {e}")
        await callback.message.answer("❌ Не вдалося надіслати відео")


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

@app.get("/")
async def root():
    return {"status": "working"}

@app.get("/ping")
async def ping():
    return {"status": "pong"}


