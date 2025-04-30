from flask import Flask, render_template, request, session, redirect, url_for
import aiosqlite
import asyncio
from flask import jsonify  # Правильно - импортирует функцию из Flask
import sys
import os
from flask_cors import CORS
# Add the server directory to Python path
server_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(server_dir)

from app.parser import staking_bp

app = Flask(__name__)
CORS(app)
app.secret_key = 'supersecretkey'
DATABASE = '../bot/referrals.db'

# Register the staking Blueprint
app.register_blueprint(staking_bp, url_prefix='/api')


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


@app.route('/api/get-balance')
async def get_balance():
    user_id = session.get('user_id') or '6850731097'  # Fallback для тестирования
    try:
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                if user:
                    return jsonify({'balance': user[0]})  # Используем flask.jsonify
                return jsonify({'balance': 0, 'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'balance': 0, 'error': str(e)}), 500


@app.route('/api/deduct-points', methods=['POST'])
async def deduct_points():
    user_id = session.get('user_id')  # Получаем user_id из сессии
    if not user_id:
        return jsonify({'success': False, 'message': 'User not authenticated'}), 401

    try:
        data = request.get_json()
        points = int(data.get('points', 0))

        if points <= 0:
            return jsonify({'success': False, 'message': 'Invalid points value'}), 400

        async with aiosqlite.connect(DATABASE) as db:
            # Проверяем текущий баланс
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                if not user:
                    return jsonify({'success': False, 'message': 'User not found'}), 404

                current_balance = user[0]
                if current_balance < points:
                    return jsonify({'success': False, 'message': 'Insufficient balance'}), 400

                # Обновляем баланс
                new_balance = current_balance - points
                await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
                await db.commit()

                return jsonify({
                    'success': True,
                    'newBalance': new_balance,
                    'deducted': points
                })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/')
async def index1():
    # Получаем user_id из query-параметров
    # убрать меня из списка
    # user_id = request.args.get('user_id')
    user_id =  '6850731097'
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


@app.route('/add_social_points', methods=['POST'])
async def add_social_points():
    # Проверяем авторизацию пользователя
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401

    try:
        # user_id = session['user_id']
        user_id='6850731097'

        # Обновляем баланс в базе данных
        async with aiosqlite.connect(DATABASE) as db:
            # Проверяем существование пользователя
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                if not user:
                    return jsonify({'success': False, 'message': 'User not found'}), 404

            # Добавляем 10 баллов
            await db.execute("UPDATE users SET balance = balance + 10 WHERE user_id = ?", (user_id,))
            await db.commit()

            # Получаем обновленный баланс
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                new_balance = (await cursor.fetchone())[0]

            return jsonify({
                'success': True,
                'new_balance': new_balance,
                'message': '+10 points added successfully'
            })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/profile_data')
async def profile_data():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401

    try:
        user = await get_user_by_id(user_id)
        posts = await get_posts_by_user_id()

        if user:
            return jsonify({
                'success': True,
                'user_id': user[0],
                'username': user[1],
                'balance': user[2],
                'posts': [
                    {
                        'title': post[0],
                        'description': post[1],
                        'link': post[2],
                        'bonus': post[3]
                    }
                    for post in posts
                ]
            })
        return jsonify({'success': False, 'message': 'User not found'}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500






@app.route('/add_bonus', methods=['POST'])
async def add_bonus():
    user_id = session.get('user_id')  # Получаем user_id из сессии
    if not user_id:
        return jsonify(success=False, message="User not logged in.")

    user = await get_user_by_id(user_id)  # Передаём user_id, а не строку 'user_id'
    if user:
        await update_user_balance(user_id, 100000)
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


@app.route('/chart')
async def chart_route():
    return render_template('Chart.html')

@app.route('/staking')
async def staking_route():  # Изменил имя функции
    return render_template('staking.html')


@app.route('/binance')
async def binance_route():  # Изменил имя функции
    return render_template('binance.html')

@app.route('/bingx')
async def bingx_route():  # Изменил имя функции
    return render_template('bingx.html')

@app.route('/bitget')
async def bitget_route():  # Изменил имя функции
    return render_template('bitget.html')

@app.route('/bybit')
async def bybit_route():  # Изменил имя функции
    return render_template('bybit.html')

@app.route('/kucoin')
async def kucoin_route():  # Изменил имя функции
    return render_template('kucoin.html')

@app.route('/okx')
async def okx_route():  # Изменил имя функции
    return render_template('okx.html')

@app.route('/xtcoin')
async def xtcoin_route():  # Изменил имя функции
    return render_template('xtcoin.html')



@app.route('/graf')
async def graf():
    # user_id = session.get('user_id')
    user_id = '6850731097'
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
    app.run(app.run(port=5001),debug=True)