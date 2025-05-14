import logging
import sqlite3
import asyncio
import pandas as pd
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from urllib.parse import quote
import io
from datetime import datetime
from typing import Union

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
API_TOKEN = "8071846167:AAH5iIcF8Z_dQ-RrmKEfxYO8mebDZ3T1uTE"
ADMIN_ID = 6850731097
WEB_APP_URL = "https://vladtichonenko.github.io/test_post1/"

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


### --- Функции работы с БД --- ###

def get_db():
    """Возвращает соединение и курсор к базе данных"""
    conn = sqlite3.connect("referrals.db")
    return conn, conn.cursor()


def create_db():
    """Создание базы данных, если её нет"""
    conn, cursor = get_db()

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            referrer_id INTEGER,
            balance INTEGER DEFAULT 100,
            referral_link TEXT,
            mining_end_time INTEGER
        )
    """)

    # Проверяем и добавляем столбец referral_link, если его нет
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'referral_link' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN referral_link TEXT")

    # Таблица постов
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
    """Добавление поста в базу данных"""
    conn, cursor = get_db()
    cursor.execute(
        "INSERT INTO posts (title, description, link, bonus) VALUES (?, ?, ?, ?)",
        (title, description, link, bonus)
    )
    conn.commit()
    conn.close()


def get_posts():
    """Получение всех постов"""
    conn, cursor = get_db()
    cursor.execute("SELECT id, title, description, link, bonus FROM posts")
    posts = cursor.fetchall()
    conn.close()
    return posts


def delete_post(post_id):
    """Удаление поста из базы данных"""
    conn, cursor = get_db()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()


def add_user(user_id, username, referrer_id=None):
    """Добавление нового пользователя"""
    conn, cursor = get_db()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))

    if cursor.fetchone() is None:
        # Генерируем реферальную ссылку
        referral_link = f"https://t.me/HistoBit_bot?start={user_id}"

        cursor.execute("""
            INSERT INTO users 
            (user_id, username, referrer_id, balance, referral_link) 
            VALUES (?, ?, ?, 100, ?)
        """, (user_id, username, referrer_id, referral_link))

        conn.commit()

        # Начисление бонусов за рефералов
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
    """Обновление баланса пользователя"""
    conn, cursor = get_db()
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (points, user_id)
    )
    conn.commit()
    conn.close()


def get_balance(user_id):
    """Получение баланса пользователя"""
    conn, cursor = get_db()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


async def notify_referrer(referrer_id, new_username, points):
    """Уведомление реферера о новом пользователе"""
    await bot.send_message(
        referrer_id,
        f"Ваш реферал @{new_username} принес вам {points} баллов!"
    )


def get_referrals(user_id):
    """Получение списка рефералов"""
    conn, cursor = get_db()
    cursor.execute("SELECT username FROM users WHERE referrer_id = ?", (user_id,))
    referrals = cursor.fetchall()
    conn.close()
    return [ref[0] for ref in referrals]


def get_all_users():
    """Получение всех пользователей с их рефералами"""
    conn, cursor = get_db()

    cursor.execute("SELECT user_id, username, balance FROM users")
    users = cursor.fetchall()

    users_data = []
    for user_id, username, balance in users:
        cursor.execute("SELECT username FROM users WHERE referrer_id = ?", (user_id,))
        referrals = cursor.fetchall()
        referrals_list = [ref[0] for ref in referrals] if referrals else []
        users_data.append({
            "user_id": user_id,
            "username": username or f"id{user_id}",
            "balance": balance,
            "referrals": referrals_list
        })

    conn.close()
    return users_data


### --- Обработчики команд --- ###

@dp.message(CommandStart())
async def send_welcome(message: Message):
    """Обработка команды /start"""
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

    # Формируем URL с данными
    posts = get_posts()
    posts_param = "|".join([f"{p[1]}~{p[2]}~{p[3]}~{p[4]}" for p in posts])
    posts_param = quote(posts_param)
    url_with_data = f"{WEB_APP_URL}?user_id={user_id}"

    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.button(text="Перейти в HistoBit", url=url_with_data)

    referral_link = f"https://t.me/HistoBit_bot?start={user_id}"
    message_text = (
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"🏆 Твой баланс: {balance} баллов\n\n"
        "Нажмите кнопку ниже, чтобы перейти в наше приложение:"
    )

    await message.answer(message_text, reply_markup=builder.as_markup())

@dp.message(Command('points'))
async def show_points(message: Message):
    """Показывает баланс пользователя"""
    await message.answer(f"Ваш баланс: {get_balance(message.from_user.id)} баллов")


@dp.message(Command('ref'))
async def show_referrals(message: Message):
    """Показывает список рефералов пользователя"""
    referrals = get_referrals(message.from_user.id)
    if referrals:
        await message.answer("Твои рефералы:\n" + "\n".join([f"@{r}" for r in referrals]))
    else:
        await message.answer("У тебя пока нет рефералов.")


async def show_all_users(source: Union[Message, CallbackQuery]):
    """Показывает всех пользователей (только для админа)"""
    if isinstance(source, CallbackQuery):
        user_id = source.from_user.id
        message = source.message
    else:
        user_id = source.from_user.id
        message = source

    if user_id != ADMIN_ID:
        await message.answer("У вас нет прав доступа к этой команде.")
        return

    users_data = get_all_users()

    if not users_data:
        await message.answer("В базе нет пользователей.")
        return

    # Формируем текстовое сообщение
    text = "📊 <b>Список всех пользователей:</b>\n\n"
    for user in users_data:
        referrals_text = ", ".join([f"@{ref}" for ref in user['referrals']]) if user['referrals'] else "нет рефералов"
        text += (
            f"👤 <b>Пользователь:</b> @{user['username']} (ID: {user['user_id']})\n"
            f"💰 <b>Баланс:</b> {user['balance']} баллов\n"
            f"👥 <b>Рефералы:</b> {referrals_text}\n"
            f"────────────────────\n"
        )

    # Создаем Excel файл
    df = pd.DataFrame([{
        'ID': user['user_id'],
        'Username': user['username'],
        'Balance': user['balance'],
        'Referrals': ", ".join(user['referrals']) if user['referrals'] else "None",
        'Referrals Count': len(user['referrals'])
    } for user in users_data])

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Users')
    excel_buffer.seek(0)

    await message.answer(text, parse_mode='HTML')
    await message.answer_document(
        types.BufferedInputFile(excel_buffer.read(), filename='users_list.xlsx'),
        caption="📋 Excel файл со списком пользователей"
    )


@dp.message(Command('admin'))
async def admin_panel(message: Message):
    """Показывает админ-панель"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав доступа к админ-панели.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить пост", callback_data="add_post")
    builder.button(text="Список пользователей", callback_data="all_users")
    builder.button(text="Просмотр и удаление постов", callback_data="view_posts")
    builder.adjust(1)

    await message.answer("Админ-панель. Выберите действие:\n\n Перейти в тех поддержку t.me/histobit_chat_bot", reply_markup=builder.as_markup())


@dp.callback_query(F.data == "add_post")
async def add_post_command(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "Введите пост в формате:\n"
        "/task <title>\n"
        "/description <desc>\n"
        "/link <link>\n"
        "/bonus <bonus>"
    )


@dp.callback_query(F.data == "all_users")
async def all_users_callback(callback: CallbackQuery):
    await callback.answer()
    await show_all_users(callback)


@dp.callback_query(F.data == "view_posts")
async def view_posts(callback: CallbackQuery):
    """Показывает список постов с кнопками удаления"""
    await callback.answer()

    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("У вас нет прав доступа к этой команде.")
        return

    posts = get_posts()
    if not posts:
        await callback.message.answer("Нет доступных постов.")
        return

    for post_id, title, description, link, bonus in posts:
        # Создаем инлайн-кнопку для удаления
        builder = InlineKeyboardBuilder()
        builder.button(text="Удалить пост", callback_data=f"delete_post_{post_id}")

        # Формируем текст поста
        text = (
            f"📝 <b>Название:</b> {title}\n"
            f"📖 <b>Описание:</b> {description}\n"
            f"🔗 <b>Ссылка:</b> {link or 'Нет ссылки'}\n"
            f"🎁 <b>Бонус:</b> {bonus} баллов"
        )

        await callback.message.answer(text, parse_mode='HTML', reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("delete_post_"))
async def delete_post_callback(callback: CallbackQuery):
    """Обработка удаления поста"""
    await callback.answer()

    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("У вас нет прав доступа к этой команде.")
        return

    # Извлекаем ID поста из callback_data
    post_id = int(callback.data.replace("delete_post_", ""))

    # Удаляем пост
    delete_post(post_id)

    # Показываем админ-панель
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить пост", callback_data="add_post")
    builder.button(text="Список пользователей", callback_data="all_users")
    builder.button(text="Просмотр и удаление постов", callback_data="view_posts")
    builder.adjust(1)

    await callback.message.answer("✅ Пост успешно удален!\nАдмин-панель. Выберите действие: \n\n Перейти в тех поддержку t.me/histobit_chat_bot",
                                  reply_markup=builder.as_markup())


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
        await message.answer("Ошибка: необходимо указать название и описание!")
        return

    add_post(title, description, link, bonus)
    await message.answer("✅ Пост успешно добавлен!")


async def on_startup():
    """Действия при запуске бота"""
    create_db()
    logger.info("Бот успешно запущен")


async def main():
    await on_startup()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())