import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
from datetime import datetime
import asyncio

# Настройка логгера
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token="7614037945:AAFrWrjShd62i_QDfqN-5YnfKNcthUXkb4w")  # ← ЗАМЕНИТЕ ТОКЕН
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Подключение к базе данных
conn = sqlite3.connect('referrals.db', check_same_thread=False)
cursor = conn.cursor()


# Классы состояний
class AnswerState(StatesGroup):
    waiting_for_answer = State()


class AddAdminState(StatesGroup):
    waiting_for_user_id = State()


class DelAdminState(StatesGroup):
    waiting_for_user_id = State()


# Конфигурация
ADMIN_ID = 6850731097  # ← ЗАМЕНИТЕ НА ВАШ ID
last_checked_id = 0


def check_database():
    """Инициализация структуры базы данных"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            admin_answer TEXT DEFAULT NULL,
            is_answered BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
    ''')

    # Добавляем главного админа если его нет
    cursor.execute('INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)',
                   (ADMIN_ID, 'Главный админ'))
    conn.commit()


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None


check_database()


async def check_new_questions():
    """Фоновая проверка новых вопросов"""
    global last_checked_id
    while True:
        await asyncio.sleep(10)
        try:
            cursor.execute(
                "SELECT COUNT(id) FROM questions WHERE id > ? AND is_answered = FALSE",
                (last_checked_id,)
            )
            new_count = cursor.fetchone()[0]

            if new_count > 0:
                await notify_admin(new_count)
                cursor.execute("SELECT MAX(id) FROM questions")
                last_checked_id = cursor.fetchone()[0] or 0

        except Exception as e:
            logging.error(f"Ошибка проверки вопросов: {e}")


async def on_startup(dp):
    """Действия при запуске бота"""
    global last_checked_id
    cursor.execute("SELECT MAX(id) FROM questions")
    last_checked_id = cursor.fetchone()[0] or 0
    asyncio.create_task(check_new_questions())


async def notify_admin(new_count: int):
    """Уведомление администраторов"""
    cursor.execute('SELECT user_id FROM admins')
    admins = cursor.fetchall()
    for admin in admins:
        try:
            await bot.send_message(admin[0], f"🔔 Новых неотвеченных вопросов: {new_count}\nПосмотреть список - /start")
        except Exception as e:
            logging.error(f"Ошибка уведомления админа {admin[0]}: {e}")

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Главное меню администратора"""
    if not is_admin(message.from_user.id):
        await message.reply("⛔ Доступ запрещен")
        return

    cursor.execute("SELECT id, question FROM questions WHERE is_answered = FALSE")
    questions = cursor.fetchall()

    if not questions:
        await message.answer("📭 Нет новых вопросов")
        return

    keyboard = types.InlineKeyboardMarkup()
    for q_id, q_text in questions:
        button_text = f"❓ {q_text[:30]}{'...' if len(q_text) > 30 else ''}"
        keyboard.add(types.InlineKeyboardButton(
            text=button_text,
            callback_data=f"question_{q_id}"
        ))

    await message.answer("📝 Список новых вопросов:", reply_markup=keyboard)

# Команды администратора
@dp.message_handler(commands=['add'])
async def add_admin_command(message: types.Message):
    """Добавление администратора"""
    x=message.from_user.id
    if x!=ADMIN_ID:
        await message.reply("⛔ Доступ запрещен")
        return

    await message.answer("Введите ID пользователя для добавления:")
    await AddAdminState.waiting_for_user_id.set()


@dp.message_handler(state=AddAdminState.waiting_for_user_id)
async def process_add_admin(message: types.Message, state: FSMContext):
    """Обработка добавления администратора"""
    try:
        user_id = int(message.text)

        # Проверяем существование пользователя через попытку отправки сообщения
        try:
            await bot.send_message(user_id, "🤖 Вы были назначены администратором!")
            username = "неизвестно"
        except Exception as e:
            await message.answer(f"❌ Ошибка: Не удалось найти пользователя. Убедитесь что:\n"
                                 f"1. Пользователь существует\n"
                                 f"2. Он запустил бота\n"
                                 f"3. ID введен правильно")
            return

        # Получаем username если доступно
        if message.forward_from:
            username = message.forward_from.username or "нет"
        else:
            cursor.execute('SELECT username FROM admins WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            username = result[0] if result else "неизвестно"

        cursor.execute('INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)',
                       (user_id, username))
        conn.commit()

        await message.answer(f"✅ Пользователь (ID: {user_id}) добавлен в администраторы!\n"
                             f"Username: @{username}")

    except ValueError:
        await message.answer("❌ Ошибка: Введите корректный ID пользователя (число)")
    except Exception as e:
        await message.answer(f"❌ Неизвестная ошибка: {str(e)}")

    await state.finish()








@dp.message_handler(commands=['del'])
async def del_admin_command(message: types.Message):
    """Удаление администратора"""
    x = message.from_user.id
    if x != ADMIN_ID:
        await message.reply("⛔ Доступ запрещен")
        return

    cursor.execute('SELECT user_id, username FROM admins')
    admins = cursor.fetchall()

    if not admins:
        await message.answer("❌ Нет зарегистрированных администраторов")
        return

    admins_list = "\n".join([f"ID: {a[0]} | Username: @{a[1]}" for a in admins])
    await message.answer(
        f"Список администраторов:\n{admins_list}\n\nВведите ID для удаления:",
        parse_mode="HTML"
    )
    await DelAdminState.waiting_for_user_id.set()


@dp.message_handler(state=DelAdminState.waiting_for_user_id)
async def process_del_admin(message: types.Message, state: FSMContext):
    """Обработка удаления администратора"""
    try:
        user_id = int(message.text)
        if user_id == ADMIN_ID:
            await message.answer("⚠️ Нельзя удалить главного администратора!")
            return

        cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
        conn.commit()

        if cursor.rowcount > 0:
            await message.answer(f"✅ Пользователь с ID {user_id} удален из администраторов!")
        else:
            await message.answer("❌ Пользователь с таким ID не найден!")

    except ValueError:
        await message.answer("❌ Ошибка: Введите корректный ID пользователя (число)")
    finally:
        await state.finish()


# Обработка вопросов



@dp.callback_query_handler(lambda c: c.data.startswith('question_'))
async def show_question_details(callback_query: types.CallbackQuery):
    """Просмотр деталей вопроса"""
    q_id = int(callback_query.data.split('_')[1])

    cursor.execute('''
        SELECT user_id, question, created_at 
        FROM questions 
        WHERE id = ?''', (q_id,))

    result = cursor.fetchone()
    if not result:
        await bot.answer_callback_query(callback_query.id, "Вопрос не найден")
        return

    user_id, question, created_at = result
    formatted_time = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")

    text = (
        f"🆔 Пользователь: {user_id}\n"
        f"🕒 Время вопроса: {formatted_time}\n"
        f"📝 Вопрос:\n{question}"
    )

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=text,
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(
                text="✍️ Ответить",
                callback_data=f"answer_{q_id}"
            )
        )
    )
    await bot.answer_callback_query(callback_query.id)


@dp.callback_query_handler(lambda c: c.data.startswith('answer_'))
async def start_answer(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало процесса ответа"""
    q_id = int(callback_query.data.split('_')[1])
    async with state.proxy() as data:
        data['question_id'] = q_id

    await AnswerState.waiting_for_answer.set()
    await bot.send_message(callback_query.from_user.id, "Введите ваш ответ:")


@dp.message_handler(state=AnswerState.waiting_for_answer)
async def save_answer(message: types.Message, state: FSMContext):
    """Сохранение ответа"""
    answer = message.text
    async with state.proxy() as data:
        q_id = data['question_id']

    cursor.execute('''
        UPDATE questions 
        SET admin_answer = ?, is_answered = TRUE 
        WHERE id = ?
    ''', (answer, q_id))
    conn.commit()

    await message.answer("✅ Ответ сохранен!")
    await state.finish()
    await send_welcome(message)


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handle_user_question(message: types.Message):
    """Обработка вопросов от пользователей"""
    if is_admin(message.from_user.id):
        return

    cursor.execute('''
        INSERT INTO questions (user_id, question)
        VALUES (?, ?)
    ''', (message.from_user.id, message.text))
    conn.commit()

    await message.answer("✅ Ваш вопрос принят! Ожидайте ответа.")
    await notify_admin(1)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)