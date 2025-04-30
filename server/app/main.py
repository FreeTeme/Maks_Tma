import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from urllib.parse import quote
from config import PARSERS
from importlib import import_module
import asyncio


API_TOKEN = "7972918156:AAGvSPb3tscthKLnEb3eQ2uvtgeVNiHbQ4U"
ADMIN_ID = 6850731097
WEB_APP_URL = "https://vladtichonenko.github.io/test_post1/"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


### --- Функции работы с БД (без изменений) --- ###

def get_db():
    conn = sqlite3.connect("referrals.db")
    return conn, conn.cursor()

def create_db():
    conn, cursor = get_db()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            referrer_id INTEGER,
            balance INTEGER DEFAULT 100,
            referral_link TEXT
        )
    """)
    
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'referral_link' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN referral_link TEXT")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            link TEXT,
            bonus INTEGER
        )
    """)
    conn.commit()
    conn.close()

def add_post(title, description, link, bonus):
    conn, cursor = get_db()
    cursor.execute("INSERT INTO posts (title, description, link, bonus) VALUES (?, ?, ?, ?)",
                   (title, description, link, bonus))
    conn.commit()
    conn.close()

def get_posts():
    conn, cursor = get_db()
    cursor.execute("SELECT title, description, link, bonus FROM posts")
    posts = cursor.fetchall()
    conn.close()
    return posts

def add_user(user_id, username, referrer_id=None):
    conn, cursor = get_db()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))

    if cursor.fetchone() is None:
        referral_link = f"https://t.me/HistoBit_bot?start={user_id}"
        cursor.execute("""
            INSERT INTO users 
            (user_id, username, referrer_id, balance, referral_link) 
            VALUES (?, ?, ?, 100, ?)
        """, (user_id, username, referrer_id, referral_link))
        conn.commit()

        if referrer_id:
            update_balance(referrer_id, 3)
            notify_referrer(referrer_id, username, 3)
            cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (referrer_id,))
            second_level_ref = cursor.fetchone()
            if second_level_ref and second_level_ref[0]:
                update_balance(second_level_ref[0], 1)
                notify_referrer(second_level_ref[0], username, 1)
    conn.close()

def update_balance(user_id, points):
    conn, cursor = get_db()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (points, user_id))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn, cursor = get_db()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

async def notify_referrer(referrer_id, new_username, points):
    await bot.send_message(referrer_id, f"Ваш реферал @{new_username} принес вам {points} баллов!")

def get_referrals(user_id):
    conn, cursor = get_db()
    cursor.execute("SELECT username FROM users WHERE referrer_id = ?", (user_id,))
    referrals = cursor.fetchall()
    conn.close()
    return [ref[0] for ref in referrals]


### --- Обработчики команд (обновленные для aiogram 3.x) --- ###

@dp.message(Command("start"))
async def send_welcome(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    referrer_id = None

    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
            if referrer_id == user_id:
                referrer_id = None
        except ValueError:
            referrer_id = None

    add_user(user_id, username, referrer_id)
    balance = get_balance(user_id)

    posts = get_posts()
    posts_param = "|".join([f"{p[0]}~{p[1]}~{p[2]}~{p[3]}" for p in posts])
    posts_param = quote(posts_param)

    url_with_data = f"{WEB_APP_URL}?user_id={user_id}"

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Перейти на сайт",
        url=url_with_data
    ))

    referral_link = f"https://t.me/HistoBit_bot?start={user_id}"
    message_text = (
        f"Привет, {message.from_user.first_name}!\n"
        f"Твой баланс: {balance} баллов\n\n"
        f"Приглашай друзей по этой ссылке и зарабатывай баллы:\n{referral_link}"
    )

    await message.answer("Нажмите кнопку ниже, чтобы перейти на сайт:", reply_markup=builder.as_markup())
    await message.answer(message_text)

@dp.message(Command("ex"))
async def show_exchange_info(message: Message):
    await message.answer("Введите тикер монеты (например, BTC, ETH, LUNA):")

@dp.message(F.text.upper() & F.text.len() <= 5)
async def process_coin_input(message: Message):
    coin = message.text.upper()
    results = []

    for parser in parsers:
        try:
            info = parser.get_staking_info(coin)
            if info:
                results.append(info)
        except Exception as e:
            logging.error(f"Error processing {parser.__class__.__name__}: {str(e)}")

    if not results:
        await message.answer(f"Данные по монете {coin} не найдены.")
        return

    message_text = f"Данные по монете {coin}:\n\n"
    for exchange in results:
        message_text += f"🔹 <b>{exchange['exchange']}</b>\n"
        if exchange['holdPosList']:
            message_text += "  Гибкий стейкинг:\n"
            for pos in exchange['holdPosList']:
                message_text += f"    - APY: {pos['apy']}%\n"
        if exchange['lockPosList']:
            message_text += "  Фиксированный стейкинг:\n"
            for pos in exchange['lockPosList']:
                message_text += f"    - APY: {pos['apy']}% на {pos['days']} дней\n"
        message_text += f"  Диапазон APY: {exchange['cost']}\n\n"

    await message.answer(message_text, parse_mode="HTML")

@dp.message(Command("points"))
async def show_points(message: Message):
    await message.answer(f"Ваш баланс: {get_balance(message.from_user.id)} баллов")

@dp.message(Command("ref"))
async def show_referrals(message: Message):
    referrals = get_referrals(message.from_user.id)
    if referrals:
        await message.answer("Твои рефералы:\n" + "\n".join([f"@{r}" for r in referrals]))
    else:
        await message.answer("У тебя пока нет рефералов.")

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id == ADMIN_ID:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="Добавить пост",
            callback_data="add_post"
        ))
        await message.reply("Админ-панель. Выберите действие:", reply_markup=builder.as_markup())
    else:
        await message.reply("У вас нет прав доступа к админ-панели.")

@dp.callback_query(F.data == "add_post")
async def add_post_command(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "Введите пост в формате:\n/task <title>\n/description <desc>\n/link <link>\n/bonus <bonus>"
    )

@dp.message(F.text.startswith("/task"))
async def handle_task(message: Message):
    data = message.text.split('\n')
    title, description, link, bonus = None, None, None, 0

    for line in data:
        if line.startswith("/task"):
            title = line.replace("/task ", "").strip()
        elif line.startswith("/description"):
            description = line.replace("/description ", "").strip()
        elif line.startswith("/link"):
            link = line.replace("/link ", "").strip()
        elif line.startswith("/bonus"):
            try:
                bonus = int(line.replace("/bonus ", "").strip())
            except ValueError:
                bonus = 0

    if not title or not description:
        await message.reply("Ошибка: необходимо указать название и описание!")
        return

    add_post(title, description, link, bonus)
    await message.reply("✅ Пост успешно добавлен!")


def load_parsers():
    parsers = []
    for parser_path in PARSERS:
        try:
            module_path, class_name = parser_path.rsplit('.', 1)
            module = import_module(module_path)
            parser_class = getattr(module, class_name)
            parsers.append(parser_class())
        except Exception as e:
            logging.error(f"Ошибка загрузки парсера {parser_path}: {str(e)}")
    return parsers


async def on_startup():
    create_db()

parsers = load_parsers()

async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    dp.startup.register(on_startup)
    asyncio.run(main())