from flask import Flask, render_template, request, session, redirect, url_for
import aiosqlite
import asyncio
import jsonify

app = Flask(__name__)

DATABASE = '../bot/database.db'


async def get_user_by_id(user_id):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT user_id, username, balance FROM user WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            return user


async def get_posts_by_user_id(user_id):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT task, description, link, bonus FROM post WHERE user_id = ?", (user_id,)) as cursor:
            posts = await cursor.fetchall()
            return posts

async def update_user_balance(user_id, amount):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE user SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()


@app.route('/')
async def index1():
    # Получаем user_id из query-параметров
    user_id = request.args.get('user_id')

    if user_id:
        # Сохраняем user_id в сессии
        session['user_id'] = user_id
        return redirect(url_for('profile'))  # Перенаправляем на страницу профиля
    else:
        return "User ID не передан."


@app.route('/profile')
async def profile():
    # Получаем user_id из сессии
    user_id = session.get('user_id')

    if user_id:
        # Получаем данные пользователя и посты из базы данных
        user = await get_user_by_id(user_id)
        posts = await get_posts_by_user_id(user_id)

        if user:
            user_id, username, balance = user
            return render_template('profile.html', user_id=user_id, username=username, balance=balance, posts=posts)
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


if __name__ == '__main__':
    app.run(debug=True)