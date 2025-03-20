import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from urllib.parse import quote
from config import PARSERS
from importlib import import_module


API_TOKEN = "8165391157:AAHJr_b-FRzZUwM5S_FTM4WLqXUqThYij_k"
ADMIN_ID = 6850731097
WEB_APP_URL = "https://vladtichonenko.github.io/test_post1/"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


### --- Функции работы с БД --- ###

def get_db():
    """ Возвращает соединение и курсор к базе данных """
    conn = sqlite3.connect("referrals.db")
    return conn, conn.cursor()


def create_db():
    """ Создание базы данных, если её нет """
    conn, cursor = get_db()

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            referrer_id INTEGER,
            balance INTEGER DEFAULT 100,
            referral_link TEXT
        )
    """)

    # Проверяем и добавляем столбец referral_link, если его нет
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'referral_link' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN referral_link TEXT")

    # Таблица постов (остается без изменений)
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
    """ Добавление поста в базу данных """
    conn, cursor = get_db()
    cursor.execute("INSERT INTO posts (title, description, link, bonus) VALUES (?, ?, ?, ?)",
                   (title, description, link, bonus))
    conn.commit()
    conn.close()


def get_posts():
    """ Получение всех постов """
    conn, cursor = get_db()
    cursor.execute("SELECT title, description, link, bonus FROM posts")
    posts = cursor.fetchall()
    conn.close()
    return posts


async def on_startup(dp):
    """ Запускается при старте бота """
    create_db()


def add_user(user_id, username, referrer_id=None):
    """ Добавление нового пользователя """
    conn, cursor = get_db()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))

    if cursor.fetchone() is None:
        # Генерируем реферальную ссылку
        referral_link = f"https://t.me/HistoBit_bot?start={user_id}"
        
        # Добавляем запись с ссылкой
        cursor.execute("""
            INSERT INTO users 
            (user_id, username, referrer_id, balance, referral_link) 
            VALUES (?, ?, ?, 100, ?)
        """, (user_id, username, referrer_id, referral_link))
        
        conn.commit()

        # Начисление бонусов за рефералов (остальное без изменений)
        if referrer_id:
            update_balance(referrer_id, 3)
            notify_referrer(referrer_id, username, 3)

            # Второй уровень рефералов
            cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (referrer_id,))
            second_level_ref = cursor.fetchone()
            if second_level_ref and second_level_ref[0]:
                update_balance(second_level_ref[0], 1)
                notify_referrer(second_level_ref[0], username, 1)

    conn.close()


def update_balance(user_id, points):
    """ Обновление баланса пользователя """
    conn, cursor = get_db()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (points, user_id))
    conn.commit()
    conn.close()


def get_balance(user_id):
    """ Получение баланса пользователя """
    conn, cursor = get_db()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


def notify_referrer(referrer_id, new_username, points):
    """ Уведомление реферера о новом пользователе """
    asyncio.create_task(bot.send_message(referrer_id, f"Ваш реферал @{new_username} принес вам {points} баллов!"))


def get_referrals(user_id):
    """ Получение списка рефералов """
    conn, cursor = get_db()
    cursor.execute("SELECT username FROM users WHERE referrer_id = ?", (user_id,))
    referrals = cursor.fetchall()
    conn.close()
    return [ref[0] for ref in referrals]


### --- Обработчики команд --- ###

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """ Обработка команды /start """
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

    # Получаем все посты из базы
    posts = get_posts()
    posts_param = "|".join([f"{p[0]}~{p[1]}~{p[2]}~{p[3]}" for p in posts])
    posts_param = quote(posts_param)  # Кодируем строку для URL

    url_with_data = f"{WEB_APP_URL}?user_id={user_id}"

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Перейти на сайт", url=url_with_data)
    )

    referral_link = f"https://t.me/HistoBit_bot?start={user_id}"
    message_text = (
        f"Привет, {message.from_user.first_name}!\n"
        f"Твой баланс: {balance} баллов\n\n"
        f"Приглашай друзей по этой ссылке и зарабатывай баллы:\n{referral_link}"
    )

    await message.answer("Нажмите кнопку ниже, чтобы перейти на сайт:", reply_markup=keyboard)
    await message.answer(message_text)


@dp.message_handler(commands=['points'])
async def show_points(message: types.Message):
    """ Показывает баланс пользователя """
    await message.answer(f"Ваш баланс: {get_balance(message.from_user.id)} баллов")


@dp.message_handler(commands=['ref'])
async def show_referrals(message: types.Message):
    """ Показывает список рефералов пользователя """
    referrals = get_referrals(message.from_user.id)
    if referrals:
        await message.answer("Твои рефералы:\n" + "\n".join([f"@{r}" for r in referrals]))
    else:
        await message.answer("У тебя пока нет рефералов.")


@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    """ Показывает админ-панель """
    if message.from_user.id == ADMIN_ID:
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Добавить пост", callback_data="add_post")
        )
        await message.reply("Админ-панель. Выберите действие:", reply_markup=keyboard)
    else:
        await message.reply("У вас нет прав доступа к админ-панели.")


@dp.callback_query_handler(lambda c: c.data == "add_post")
async def add_post_command(callback_query: CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id,
                           "Введите пост в формате:\n/task <title>\n/description <desc>\n/link <link>\n/bonus <bonus>")

@dp.message_handler(lambda message: message.text.startswith("/task"))
async def handle_task(message: types.Message):
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
    """ Загружает парсеры из конфигурации """
    parsers = []
    for parser_path in PARSERS:
        try:
            # Разделяем путь на модуль и имя класса
            module_path, class_name = parser_path.rsplit('.', 1)
            # Импортируем модуль
            module = import_module(module_path)
            # Получаем класс парсера
            parser_class = getattr(module, class_name)
            # Создаем экземпляр парсера и добавляем в список
            parsers.append(parser_class())
        except Exception as e:
            logging.error(f"Ошибка загрузки парсера {parser_path}: {str(e)}")
    return parsers


parsers = load_parsers()

@dp.message_handler(commands=['ex'])
async def show_exchange_info(message: types.Message):
    """ Обработка команды /ex """
    # Создаем клавиатуру для выбора монеты
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("BTC", callback_data="coin_BTC"),
        InlineKeyboardButton("ETH", callback_data="coin_ETH"),
        InlineKeyboardButton("LUNA", callback_data="coin_LUNA"),
        InlineKeyboardButton("USDT", callback_data="coin_USDT"),
    )
    await message.answer("Выберите монету:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith("coin_"))
async def process_coin_selection(callback_query: CallbackQuery):
    """ Обработка выбора монеты """
    await bot.answer_callback_query(callback_query.id)
    
    coin = callback_query.data.split("_")[1]  # Получаем выбранную монету
    results = []

    # Получаем данные от всех парсеров
    for parser in parsers:
        try:
            info = parser.get_staking_info(coin)
            if info:
                results.append(info)
        except Exception as e:
            logging.error(f"Error processing {parser.__class__.__name__}: {str(e)}")

    if not results:
        await bot.send_message(callback_query.from_user.id, f"Данные по монете {coin} не найдены.")
        return

    # Формируем сообщение с данными
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

    await bot.send_message(callback_query.from_user.id, message_text, parse_mode="HTML")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
