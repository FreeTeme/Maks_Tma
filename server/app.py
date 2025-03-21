from flask import Flask, render_template, request, session, redirect, url_for
import aiosqlite
import asyncio
import jsonify 


app = Flask(__name__)
app.secret_key = 'supersecretkey'
DATABASE = '../bot/referrals.db'


# Добавьте в app.py
async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                admin_answer TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

# Добавьте в начало приложения
@app.before_request
async def initialize():
    await init_db()


async def get_user_by_id(user_id):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT user_id, username, balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            return user


async def get_posts_by_user_id():
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT title, description, link, bonus FROM posts") as cursor:
            posts = await cursor.fetchall()
            return posts

async def update_user_balance(user_id, amount):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()


@app.route('/')
async def index1():
    # Получаем user_id из query-параметров
    # убрать меня из списка
    user_id = request.args.get('user_id')
    # user_id =  '6850731097'
    #
    if user_id:
        # Сохраняем user_id в сессии
        session['user_id'] = user_id
        return redirect(url_for('profile'))  # Перенаправляем на страницу профиля
    else:
        return "User ID не передан."
    #
    # session['user_id'] = user_id
    # return redirect(url_for('profile'))

@app.route('/profile')
async def profile():
    # Получаем user_id из сессии
    user_id = session.get('user_id')

    if user_id:
        # Получаем данные пользователя и посты из базы данных
        user = await get_user_by_id(user_id)
        posts = await get_posts_by_user_id()

        if user:
            user_id, username, balance = user
            return render_template('index1.html', user_id=user_id, username=username, balance=balance, posts=posts)
        else:
            return "Пользователь не найден."
    else:
        return "Сессия не найдена. Пожалуйста, перейдите на сайт через бота."


@app.route('/add_bonus', methods=['POST'])
async def add_bonus():
    user_id = session.get('user_id')
    user = await get_user_by_id('user_id')
    if user:
        user_id = user[0]
        await update_user_balance(user_id, 10)
        return jsonify(success=True, message="Bonus added!")
    return jsonify(success=False, message="User not found.")


async def get_referral_info(user_id):
    async with aiosqlite.connect(DATABASE) as db:
        # Получаем реферальную ссылку и количество рефералов
        async with db.execute(
                "SELECT referral_link, "
                "(SELECT COUNT(*) FROM users WHERE referrer_id = ?) AS referral_count "
                "FROM users WHERE user_id = ?",
                (user_id, user_id)
        ) as cursor:
            return await cursor.fetchone()


async def get_referrals(user_id):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT user_id, username, balance "
                "FROM users WHERE referrer_id = ?",
                (user_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_top_referral(user_id):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT username, balance "
                "FROM users WHERE referrer_id = ? "
                "ORDER BY balance DESC LIMIT 1",
                (user_id,)
        ) as cursor:
            return await cursor.fetchone()


# Функция сохранения вопроса в БД
async def save_question(user_id, question):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT INTO questions (user_id, question) VALUES (?, ?)",
            (user_id, question)
        )
        await db.commit()


# Функция получения истории чата
async def get_user_chat(user_id):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute('''
            SELECT question, admin_answer, created_at 
            FROM questions 
            WHERE user_id = ? 
            ORDER BY created_at
        ''', (user_id,)) as cursor:
            return await cursor.fetchall()


# Маршрут для отображения чата
@app.route('/chat')
async def chat():
    user_id = '6850731097'  # Фиксированный ID вместо session.get('user_id')

    chat_history = await get_user_chat(user_id)
    return render_template('result.html', chat_history=chat_history)


# Инициализация таблицы для чата (в составе init_db)
async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                admin_answer TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()



@app.route('/submit_question', methods=['POST'])
async def submit_question():
    user_id = '6850731097' # Используйте user_id из сессии вместо фиксированного значения
    if not user_id:
        return redirect(url_for('index1'))
    question = request.form.get('question')
    await save_question(user_id, question)
    return redirect(url_for('chat'))

# @app.route('/ask', methods=['POST'])
# async def ask_question():
#     user_id = '6850731097'
#     question = request.form.get('question')
#     await save_question(user_id, question)
#     return redirect(url_for('chat'))




@app.route('/graf')
async def graf():
    user_id = session.get('user_id')
    if not user_id:
        return "Сессия не найдена. Пожалуйста, перейдите на сайт через бота."

    # Получаем данные из БД
    referral_link, referral_count = await get_referral_info(user_id)
    referrals = await get_referrals(user_id)
    top_referral = await get_top_referral(user_id)

    return render_template(
        'graf.html',
        referral_link=referral_link,
        referral_count=referral_count,
        referrals=referrals,
        top_referral=top_referral
    )



if __name__ == '__main__':
    app.run(debug=True)