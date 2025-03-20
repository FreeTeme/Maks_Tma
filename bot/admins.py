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


# Класс состояний для ответа
class AnswerState(StatesGroup):
    waiting_for_answer = State()


# Конфигурация
ADMIN_ID = 622077354 # ← ЗАМЕНИТЕ НА ВАШ ID
last_checked_id = 0  # Для отслеживания новых вопросов


def check_database():
    """Проверка и создание необходимой структуры БД"""
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
    conn.commit()


check_database()




async def check_new_questions():
    """Фоновая проверка новых вопросов"""
    global last_checked_id  # Перенесем объявление сюда
    while True:
        await asyncio.sleep(10)
        try:
            # Используем текущее значение last_checked_id
            cursor.execute(
                "SELECT COUNT(id) FROM questions WHERE id > ? AND is_answered = FALSE",
                (last_checked_id,)
            )
            new_count = cursor.fetchone()[0]

            if new_count > 0:
                await notify_admin(new_count)
                # Обновляем значение после проверки
                cursor.execute("SELECT MAX(id) FROM questions")
                last_checked_id = cursor.fetchone()[0] or 0

        except Exception as e:
            logging.error(f"Ошибка проверки вопросов: {e}")


async def on_startup(dp):
    """Действия при запуске бота"""
    global last_checked_id  # Объявляем глобальную переменную здесь
    cursor.execute("SELECT MAX(id) FROM questions")
    last_checked_id = cursor.fetchone()[0] or 0
    asyncio.create_task(check_new_questions())


async def notify_admin(new_count: int):
    """Отправка уведомления администратору"""
    try:
        await bot.send_message(ADMIN_ID, f"🔔 Новых неотвеченных вопросов: {new_count}\n посмотреть список - /start")
    except Exception as e:
        logging.error(f"Ошибка уведомления: {e}")


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Обработчик команды /start"""
    if message.from_user.id != ADMIN_ID:
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


@dp.callback_query_handler(lambda c: c.data.startswith('question_'))
async def show_question_details(callback_query: types.CallbackQuery):
    """Показ деталей вопроса"""
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
        chat_id=ADMIN_ID,
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
    await bot.send_message(ADMIN_ID, "Введите ваш ответ:")


@dp.message_handler(state=AnswerState.waiting_for_answer)
async def save_answer(message: types.Message, state: FSMContext):
    """Сохранение ответа в БД"""
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
    await send_welcome(message)  # Обновляем список вопросов


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handle_user_question(message: types.Message):
    """Обработка вопросов от пользователей"""
    if message.from_user.id == ADMIN_ID:
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