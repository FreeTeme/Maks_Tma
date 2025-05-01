import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import sqlite3
from datetime import datetime
import asyncio

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота с новым синтаксисом
bot = Bot(
    token="7614037945:AAFrWrjShd62i_QDfqN-5YnfKNcthUXkb4w")
    # default=DefaultBotProperties(parse_mode=ParseMode.HTML)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключение к базе данных
conn = sqlite3.connect('referrals.db', check_same_thread=False)
cursor = conn.cursor()

# Конфигурация
ADMIN_ID = 6850731097  # ← ЗАМЕНИТЕ НА ВАШ ID
last_checked_id = 0

# Классы состояний
class AnswerState(StatesGroup):
    waiting_for_answer = State()

class AddAdminState(StatesGroup):
    waiting_for_user_id = State()

class DelAdminState(StatesGroup):
    waiting_for_user_id = State()

# Middleware для проверки админа
class AdminMiddleware:
    async def __call__(self, handler, event, data):
        if event.from_user.id == ADMIN_ID or is_admin(event.from_user.id):
            return await handler(event, data)
        await event.answer("⛔ Доступ запрещен")
        return

# Инициализация базы данных
def check_database():
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

    cursor.execute('INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)',
                  (ADMIN_ID, 'Главный админ'))
    conn.commit()

def is_admin(user_id: int) -> bool:
    cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

check_database()

# Фоновые задачи
async def check_new_questions():
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
            logger.error(f"Ошибка проверки вопросов: {e}")

async def notify_admin(new_count: int):
    cursor.execute('SELECT user_id FROM admins')
    admins = cursor.fetchall()
    for admin in admins:
        try:
            await bot.send_message(
                admin[0], 
                f"🔔 Новых неотвеченных вопросов: {new_count}\nПосмотреть список - /start"
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления админа {admin[0]}: {e}")

# Обработчики команд
@dp.message(CommandStart())
async def send_welcome(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return

    cursor.execute("SELECT id, question FROM questions WHERE is_answered = FALSE")
    questions = cursor.fetchall()

    if not questions:
        await message.answer("📭 Нет новых вопросов")
        return

    builder = InlineKeyboardBuilder()
    for q_id, q_text in questions:
        builder.button(
            text=f"❓ {q_text[:30]}{'...' if len(q_text) > 30 else ''}",
            callback_data=f"question_{q_id}"
        )
    builder.adjust(1)
    
    await message.answer("📝 Список новых вопросов:", reply_markup=builder.as_markup())

@dp.message(Command('add'))
async def add_admin_command(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещен")
        return

    await message.answer("Введите ID пользователя для добавления:")
    await state.set_state(AddAdminState.waiting_for_user_id)

@dp.message(AddAdminState.waiting_for_user_id)
async def process_add_admin(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        try:
            await bot.send_message(user_id, "🤖 Вы были назначены администратором!")
            username = "неизвестно"
        except Exception:
            await message.answer(
                "❌ Ошибка: Не удалось найти пользователя. Убедитесь что:\n"
                "1. Пользователь существует\n"
                "2. Он запустил бота\n"
                "3. ID введен правильно"
            )
            return

        cursor.execute(
            'INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)',
            (user_id, username)
        )
        conn.commit()

        await message.answer(
            f"✅ Пользователь (ID: {user_id}) добавлен в администраторы!\n"
            f"Username: @{username}"
        )
    except ValueError:
        await message.answer("❌ Ошибка: Введите корректный ID пользователя (число)")
    finally:
        await state.clear()

@dp.message(Command('del'))
async def del_admin_command(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещен")
        return

    cursor.execute('SELECT user_id, username FROM admins')
    admins = cursor.fetchall()

    if not admins:
        await message.answer("❌ Нет зарегистрированных администраторов")
        return

    admins_list = "\n".join([f"ID: {a[0]} | Username: @{a[1]}" for a in admins])
    await message.answer(
        f"Список администраторов:\n{admins_list}\n\nВведите ID для удаления:"
    )
    await state.set_state(DelAdminState.waiting_for_user_id)

@dp.message(DelAdminState.waiting_for_user_id)
async def process_del_admin(message: Message, state: FSMContext):
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
        await state.clear()

# Обработчики вопросов
@dp.callback_query(F.data.startswith('question_'))
async def show_question_details(callback: CallbackQuery):
    q_id = int(callback.data.split('_')[1])

    cursor.execute('''
        SELECT user_id, question, created_at 
        FROM questions 
        WHERE id = ?''', (q_id,))

    result = cursor.fetchone()
    if not result:
        await callback.answer("Вопрос не найден")
        return

    user_id, question, created_at = result
    formatted_time = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")

    text = (
        f"🆔 Пользователь: {user_id}\n"
        f"🕒 Время вопроса: {formatted_time}\n"
        f"📝 Вопрос:\n{question}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Ответить", callback_data=f"answer_{q_id}")

    await callback.message.answer(
        text=text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith('answer_'))
async def start_answer(callback: CallbackQuery, state: FSMContext):
    q_id = int(callback.data.split('_')[1])
    await state.update_data(question_id=q_id)
    await state.set_state(AnswerState.waiting_for_answer)
    await callback.message.answer("Введите ваш ответ:")
    await callback.answer()

@dp.message(AnswerState.waiting_for_answer)
async def save_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    q_id = data['question_id']

    cursor.execute('''
        UPDATE questions 
        SET admin_answer = ?, is_answered = TRUE 
        WHERE id = ?
    ''', (message.text, q_id))
    conn.commit()

    await message.answer("✅ Ответ сохранен!")
    await state.clear()
    await send_welcome(message)

@dp.message()
async def handle_user_question(message: Message):
    if is_admin(message.from_user.id):
        return

    cursor.execute('''
        INSERT INTO questions (user_id, question)
        VALUES (?, ?)
    ''', (message.from_user.id, message.text))
    conn.commit()

    await message.answer("✅ Ваш вопрос принят! Ожидайте ответа.")
    await notify_admin(1)

# Запуск бота
async def on_startup():
    global last_checked_id
    cursor.execute("SELECT MAX(id) FROM questions")
    last_checked_id = cursor.fetchone()[0] or 0
    asyncio.create_task(check_new_questions())

async def main():
    await on_startup()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())