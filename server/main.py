# import jupytext
from datetime import datetime, timedelta
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import os
import sys
from flask_cors import CORS
from app.parser import staking_bp
import pandas as pd
import requests
import numpy as np
import time
from analize.main import strategy_bp
from ai.main import get_full_historical_data

# Добавляем путь для импорта main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Add the server directory to Python path
server_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(server_dir)

# Импортируем Blueprint для анализа паттернов
from ai.pattern_blueprint import pattern_bp
import atexit

app = Flask(__name__)
CORS(app)
app.secret_key = 'supersecretkey'
DATABASE = '../bot/referrals.db'

app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Register the staking Blueprint
app.register_blueprint(staking_bp, url_prefix='/api')
# Register the pattern analysis Blueprint
app.register_blueprint(pattern_bp)

app.register_blueprint(strategy_bp)

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Создание таблицы для паролей и ролей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            password TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создание таблицы для логирования входов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN NOT NULL
        )
    ''')
    
    # Вставляем пароли если их еще нет
    passwords_data = [
        ('0397', 'работник'),
        ('2323', 'работник'),
        ('2121', 'работник'),
        ('1818', 'работник'),
        ('9779', 'работник'),
        ('6860', 'админ')
    ]
    
    for password, role in passwords_data:
        cursor.execute('''
            INSERT OR IGNORE INTO auth_passwords (password, role) 
            VALUES (?, ?)
        ''', (password, role))
    
    # Создание таблицы questions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            admin_answer TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Создание таблицы completed_tasks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS completed_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, post_id)
        )
    ''')

    # Создание таблицы posts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            link TEXT NOT NULL,
            bonus INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            wallet_address TEXT NOT NULL,
            coins INTEGER NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            tx_hash TEXT NOT NULL UNIQUE,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Добавляем индекс для быстрого поиска по пользователю
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_purchases_user_id 
        ON purchases(user_id)
    ''')
    
    # Добавляем индекс для предотвращения дублирования транзакций
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_purchases_tx_hash 
        ON purchases(tx_hash)
    ''')
    # Проверка и добавление столбца mining_end_time
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'mining_end_time' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN mining_end_time INTEGER")

    # Проверка и добавление столбца wallet_address
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'wallet_address' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN wallet_address TEXT")
    
    conn.commit()
    conn.close()

# Initialize database at startup
init_db()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def check_password(password):
    """Проверяет пароль и возвращает роль пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT role FROM auth_passwords 
        WHERE password = ? AND is_active = 1
    ''', (password,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def log_login_attempt(password, role, ip_address, user_agent, success):
    """Логирует попытку входа"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO login_logs (password, role, ip_address, user_agent, success)
        VALUES (?, ?, ?, ?, ?)
    ''', (password, role, ip_address, user_agent, success))
    conn.commit()
    conn.close()

def is_authenticated():
    """Проверяет, аутентифицирован ли пользователь"""
    return 'authenticated' in session and session['authenticated'] == True

def require_auth(f):
    """Декоратор для проверки аутентификации"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Декоратор для проверки роли админа"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login'))
        if session.get('user_role') != 'админ':
            return jsonify({'success': False, 'message': 'Доступ запрещен. Требуются права администратора.'}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_referral_info(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT referral_link, "
        "(SELECT COUNT(*) FROM users WHERE referrer_id = ?) AS referral_count "
        "FROM users WHERE user_id = ?",
        (user_id, user_id)
    )
    result = cursor.fetchone()
    conn.close()
    return result

def get_referrals(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username, balance "
        "FROM users WHERE referrer_id = ?",
        (user_id,)
    )
    result = cursor.fetchall()
    conn.close()
    return result

def get_top_referral(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, balance "
        "FROM users WHERE referrer_id = ? "
        "ORDER BY balance DESC LIMIT 1",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result

def save_question(user_id, question):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO questions (user_id, question) VALUES (?, ?)",
        (user_id, question)
    )
    conn.commit()
    conn.close()

def get_user_chat(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT question, admin_answer, created_at 
        FROM questions 
        WHERE user_id = ? 
        ORDER BY created_at
    ''', (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, balance FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_posts_by_user_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.title, p.description, p.link, p.bonus, p.id
        FROM posts p
        LEFT JOIN completed_tasks ct ON p.id = ct.post_id AND ct.user_id = ?
        WHERE ct.post_id IS NULL
    """, (user_id,))
    posts = cursor.fetchall()
    conn.close()
    return posts

def update_user_balance(user_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

@app.route('/disconnect_wallet', methods=['POST'])
@require_auth
def disconnect_wallet():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(success=False, message="User not logged in")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Удаляем кошелек из профиля пользователя
        cursor.execute("UPDATE users SET wallet_address = NULL WHERE user_id = ?", (user_id,))
        
        # Также можно удалить связанные данные, если нужно
        # cursor.execute("DELETE FROM wallet_sessions WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        # Очищаем сессию, если нужно
        # session.pop('wallet_address', None)
        
        return jsonify(success=True, message="Wallet disconnected")
    
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

@app.route('/save_purchase', methods=['POST'])
@require_auth
def save_purchase():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(success=False, message="User not logged in")

    try:
        data = request.get_json()
        required_fields = [ 'wallet_address', 'coins', 'amount', 'currency', 'tx_hash']
        
        # Проверяем наличие всех обязательных полей
        if not all(field in data for field in required_fields):
            return jsonify(success=False, message="Missing required fields"), 400
        
        # Проверяем типы данных
        try:
            coins = int(data['coins'])
            amount = float(data['amount'])
        except (ValueError, TypeError):
            return jsonify(success=False, message="Invalid data types"), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, не существует ли уже такая транзакция
        cursor.execute("SELECT id FROM purchases WHERE tx_hash = ?", (data['tx_hash'],))
        if cursor.fetchone():
            conn.close()
            return jsonify(success=False, message="Transaction already processed"), 409
        
        # Сохраняем покупку
        cursor.execute('''
            INSERT INTO purchases 
            (user_id, wallet_address, coins, amount, currency, tx_hash) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data['wallet_address'],
            coins,
            amount,
            data['currency'],
            data['tx_hash']
        ))
        
        # Обновляем баланс пользователя
        cursor.execute('''
            UPDATE users SET balance = balance + ? 
            WHERE user_id = ?
        ''', (coins, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify(success=True, message="Purchase saved successfully")
        
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify(success=False, message=f"Database error: {str(e)}"), 500
    except Exception as e:
        return jsonify(success=False, message=f"Server error: {str(e)}"), 500

@app.route('/api/get-balance')
@require_auth
def get_balance():
    user_id = session.get('user_id', '622077354')
    try:
        conn = get_db_connection()
        user = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()

        if user:
            return jsonify({'balance': user[0]})
        return jsonify({'balance': 0, 'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'balance': 0, 'error': str(e)}), 500

@app.route('/api/deduct-points', methods=['POST'])
@require_auth
def deduct_points():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not authenticated'}), 401

    try:
        data = request.get_json()
        points = int(data.get('points', 0))

        if points <= 0:
            return jsonify({'success': False, 'message': 'Invalid points value'}), 400

        conn = get_db_connection()
        user = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()

        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'}), 404

        current_balance = user[0]
        if current_balance < points:
            conn.close()
            return jsonify({'success': False, 'message': 'Insufficient balance'}), 400

        new_balance = current_balance - points
        conn.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'newBalance': new_balance,
            'deducted': points
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/')
def index():
    # Проверяем аутентификацию
    if not is_authenticated():
        return redirect(url_for('login'))
    
    user_id = request.args.get('user_id', '622077354')
    if user_id:
        session['user_id'] = user_id
        return redirect(url_for('profile'))
    return "Пожалуйста, укажите user_id в параметрах URL (?user_id=...)"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # Если уже аутентифицирован, перенаправляем
        if is_authenticated():
            return redirect(url_for('index'))
        return render_template('login.html')
    
    # POST запрос - проверка пароля
    password = request.form.get('password', '').strip()
    
    if not password:
        return jsonify({
            'success': False,
            'message': 'Пароль не может быть пустым'
        })
    
    # Получаем информацию о клиенте
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    # Проверяем пароль
    role = check_password(password)
    
    if role:
        # Успешный вход
        session['authenticated'] = True
        session['user_role'] = role
        session['login_time'] = datetime.now().isoformat()
        
        # Логируем успешный вход
        log_login_attempt(password, role, ip_address, user_agent, True)
        
        return jsonify({
            'success': True,
            'message': f'Добро пожаловать! Роль: {role}',
            'redirect_url': url_for('index')
        })
    else:
        # Неудачный вход
        log_login_attempt(password, 'неизвестно', ip_address, user_agent, False)
        
        return jsonify({
            'success': False,
            'message': 'Неверный пароль. Доступ запрещен.'
        })

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/tonconnect-manifest.json')
def tonconnect_manifest():
    base_url = request.host_url.rstrip('/')
    return jsonify({
        "name": "Crypto Dashboard",
        "url": base_url,
        "iconUrl": f"{base_url}/static/ton-connect-icon.png",
        "termsOfUseUrl": f"{base_url}/terms",
        "privacyPolicyUrl": f"{base_url}/privacy",
        "manifestUrl": f"{base_url}/tonconnect-manifest.json"
    }), 200, {'Content-Type': 'application/json'}

@app.route('/save_wallet', methods=['POST'])
@require_auth
def save_wallet():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(success=False, message="User not logged in")
    
    data = request.get_json()
    wallet_address = data.get('wallet_address')
    
    if not wallet_address:
        return jsonify(success=False, message="No wallet address provided")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем наличие столбца wallet_address
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'wallet_address' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN wallet_address TEXT")
            conn.commit()
        
        # Обновляем адрес кошелька
        cursor.execute(
            "UPDATE users SET wallet_address = ? WHERE user_id = ?",
            (wallet_address, user_id)
        )
        conn.commit()
        conn.close()
        
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e))

@app.route('/profile')
@require_auth
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))

    user = get_user_by_id(user_id)
    posts = get_posts_by_user_id(user_id)

    if not user:
        return "Пользователь не найден", 404

    return render_template(
        'index1.html',
        user_id=user[0],
        username=user[1],
        balance=user[2],
        posts=posts
    )

@app.route('/add_bonus', methods=['POST'])
@require_auth
def add_bonus():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(success=False, message="User not logged in.")

    user = get_user_by_id(user_id)
    if user:
        update_user_balance(user_id, 20)
        return jsonify(success=True, message="Bonus added!")
    return jsonify(success=False, message="User not found.")

@app.route('/api/get_mining_timer', methods=['GET'])
@require_auth
def get_mining_timer():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not logged in'})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT mining_end_time FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0]:
        return jsonify({'success': True, 'end_time': result[0]})
    return jsonify({'success': False, 'message': 'No active mining session'})

@app.route('/api/set_mining_timer', methods=['POST'])
@require_auth
def set_mining_timer():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not logged in'})

    end_time = request.json.get('end_time')
    if not end_time:
        return jsonify({'success': False, 'message': 'No end_time provided'})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET mining_end_time = ? WHERE user_id = ?", (end_time, user_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/clear_mining_timer', methods=['POST'])
@require_auth
def clear_mining_timer():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not logged in'})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET mining_end_time = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/chat')
@require_auth
def chat():
    user_id = session.get('user_id', '622077354')
    chat_history = get_user_chat(user_id)
    return render_template('result.html', chat_history=chat_history)

@app.route('/submit_question', methods=['POST'])
@require_auth
def submit_question():
    user_id = session.get('user_id', '622077354')
    if not user_id:
        return redirect(url_for('index'))
    question = request.form.get('question')
    save_question(user_id, question)
    return redirect(url_for('chat'))

@app.route('/api/save_search', methods=['POST'])
@require_auth
def save_search():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not authenticated'}), 401

    data = request.get_json()
    search_query = data.get('search_query')
    if not search_query:
        return jsonify({'success': False, 'message': 'No search query provided'}), 400

    session['last_staking_search'] = search_query
    return jsonify({'success': True, 'message': 'Search query saved'})

@app.route('/api/get_last_search', methods=['GET'])
@require_auth
def get_last_search():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not authenticated'}), 401

    last_search = session.get('last_staking_search')
    if last_search:
        return jsonify({'success': True, 'last_search': last_search})
    return jsonify({'success': False, 'message': 'No previous search found'})

@app.route('/chart')
@require_auth
def chart_route():
    return render_template('Chart.html')

@app.route('/staking')
@require_auth
def staking_route():
    return render_template('staking.html')

@app.route('/binance')
@require_auth
def binance_route():
    return render_template('binance.html')

@app.route('/bingx')
@require_auth
def bingx_route():
    return render_template('bingx.html')

@app.route('/bitget')
@require_auth
def bitget_route():
    return render_template('bitget.html')

@app.route('/bybit')
@require_auth
def bybit_route():
    return render_template('bybit.html')

# Аналитика паттернов - роутинг для UI страницы
@app.route('/pattern')
@require_auth
def analysis():
    return render_template('pattern.html')

@app.route('/kucoin')
@require_auth
def kucoin_route():
    return render_template('kucoin.html')

@app.route('/okx')
@require_auth
def okx_route():
    return render_template('okx.html')

@app.route('/xtcom')
@require_auth
def xtcoin_route():
    return render_template('xtcom.html')

@app.route('/mexc')
@require_auth
def mexc_route():
    return render_template('mexc.html')

@app.route('/gateio')
@require_auth
def gateio_route():
    return render_template('gateio.html')

@app.route('/htx')
@require_auth
def htx_route():
    return render_template('htx.html')

@app.route('/bitmart')
@require_auth
def bitmart_route():
    return render_template('bitmart.html')

@app.route('/wallet')
@require_auth
def wallet_route():
    return render_template('wallet.html')

@app.route('/graf')
@require_auth
def graf():
    user_id = session.get('user_id', '622077354')
    if not user_id:
        return "Сессия не найдена. Пожалуйста, перейдите на сайт через бота."

    referral_info = get_referral_info(user_id)
    if referral_info:
        referral_link, referral_count = referral_info
    else:
        referral_link, referral_count = None, 0

    referrals = get_referrals(user_id)
    top_referral = get_top_referral(user_id)

    return render_template(
        'graf.html',
        referral_link=referral_link,
        referral_count=referral_count,
        referrals=referrals,
        top_referral=top_referral
    )

@app.route('/add_social_points', methods=['POST'])
@require_auth
def add_social_points():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(success=False, message="User not logged in.")

    data = request.get_json()
    bonus = data.get('bonus', 20)

    user = get_user_by_id(user_id)
    if user:
        update_user_balance(user_id, bonus)
        return jsonify(success=True, new_balance=user[2] + bonus, message="Bonus added!")
    return jsonify(success=False, message="User not found.")

@app.route('/complete_social_task', methods=['POST'])
@require_auth
def complete_social_task():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(success=False, message="User not logged in")

    data = request.get_json()
    bonus = data.get('bonus', 0)
    post_id = data.get('post_id')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM completed_tasks WHERE user_id = ? AND post_id = ?", 
                      (user_id, post_id))
        if cursor.fetchone():
            conn.close()
            return jsonify(success=False, message="Task already completed")

        cursor.execute("INSERT INTO completed_tasks (user_id, post_id) VALUES (?, ?)",
                      (user_id, post_id))

        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?",
                      (bonus, user_id))

        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        new_balance = cursor.fetchone()[0]

        conn.commit()
        conn.close()
        return jsonify(success=True, new_balance=new_balance)

    except Exception as e:
        conn.rollback()
        return jsonify(success=False, message=str(e))

@app.route('/get_completed_tasks')
@require_auth
def get_completed_tasks():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(success=False, message="User not logged in")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT post_id FROM completed_tasks WHERE user_id = ?", (user_id,))
        completed_tasks = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify(success=True, completed_tasks=completed_tasks)
    except Exception as e:
        return jsonify(success=False, message=str(e))

@app.route('/api/get_chat')
@require_auth
def get_chat():
    user_id = session.get('user_id', '622077354')
    chat_history = get_user_chat(user_id)
    # Преобразуем историю чата в список словарей для JSON
    chat_data = [
        {
            'question': message['question'],
            'admin_answer': message['admin_answer'],
            'created_at': message['created_at']
        } for message in chat_history
    ]
    return jsonify({'chat_history': chat_data})


# Глобальная переменная для хранения данных OHLCV
ohlcv_df = None

def load_ohlcv_data():
    """Загрузка данных OHLCV при запуске приложения"""
    global ohlcv_df
    try:
        # Загружаем полные исторические данные через функцию из main.py
        ohlcv_df = get_full_historical_data()
        print(f"Загружено {len(ohlcv_df)} записей OHLCV")
    except Exception as e:
        print(f"Ошибка при загрузке данных OHLCV: {e}")
        ohlcv_df = pd.DataFrame()

# Загружаем данные при запуске приложения
load_ohlcv_data()

# УДАЛЕНЫ ДУБЛИРУЮЩИЕСЯ ЭНДПОИНТЫ, КОТОРЫЕ ПЕРЕМЕЩЕНЫ В pattern_blueprint.py:
# - /api/pattern_bounds
# - /api/ohlcv  
# - /analyze_pattern
# - /api/update_status
# - /api/force_update
# - /api/update_settings

# Добавляем в импорты app.py
import atexit


# Админ маршруты
@app.route('/admin/logs')
@require_admin
def admin_logs():
    """Страница логов для админа"""
    return render_template('admin_logs.html')

@app.route('/api/admin/stats')
@require_admin
def admin_stats():
    """Статистика входов"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Общее количество входов
        cursor.execute("SELECT COUNT(*) FROM login_logs")
        total_logins = cursor.fetchone()[0]
        
        # Успешные входы
        cursor.execute("SELECT COUNT(*) FROM login_logs WHERE success = 1")
        successful_logins = cursor.fetchone()[0]
        
        # Неудачные входы
        cursor.execute("SELECT COUNT(*) FROM login_logs WHERE success = 0")
        failed_logins = cursor.fetchone()[0]
        
        # Уникальные IP
        cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM login_logs WHERE ip_address IS NOT NULL")
        unique_ips = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_logins': total_logins,
                'successful_logins': successful_logins,
                'failed_logins': failed_logins,
                'unique_ips': unique_ips
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/check-admin')
@require_auth
def check_admin():
    """Проверяет, является ли пользователь админом"""
    is_admin = session.get('user_role') == 'админ'
    return jsonify({
        'success': True,
        'is_admin': is_admin,
        'role': session.get('user_role', 'неизвестно')
    })




@app.route('/api/admin/passwords')
@require_admin
def get_passwords():
    """Получение списка всех паролей (кроме админского)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, password, role, is_active, created_at 
            FROM auth_passwords 
            WHERE role != 'админ'
            ORDER BY created_at DESC
        ''')
        passwords = cursor.fetchall()
        conn.close()
        
        passwords_list = []
        for pwd in passwords:
            passwords_list.append({
                'id': pwd['id'],
                'password': pwd['password'],
                'role': pwd['role'],
                'is_active': bool(pwd['is_active']),
                'created_at': pwd['created_at']
            })
        
        return jsonify({'success': True, 'passwords': passwords_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/passwords', methods=['POST'])
@require_admin
def add_password():
    """Добавление нового пароля"""
    try:
        data = request.get_json()
        password = data.get('password', '').strip()
        role = data.get('role', 'работник')
        
        if not password:
            return jsonify({'success': False, 'message': 'Пароль не может быть пустым'}), 400
        
        if len(password) < 4:
            return jsonify({'success': False, 'message': 'Пароль должен содержать минимум 4 символа'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, не существует ли уже такой пароль
        cursor.execute('SELECT id FROM auth_passwords WHERE password = ?', (password,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Такой пароль уже существует'}), 400
        
        cursor.execute('''
            INSERT INTO auth_passwords (password, role) 
            VALUES (?, ?)
        ''', (password, role))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Пароль успешно добавлен'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/passwords/<int:password_id>', methods=['PUT'])
@require_admin
def update_password(password_id):
    """Обновление пароля"""
    try:
        data = request.get_json()
        new_password = data.get('password', '').strip()
        is_active = data.get('is_active', True)
        
        if not new_password:
            return jsonify({'success': False, 'message': 'Пароль не может быть пустым'}), 400
        
        if len(new_password) < 4:
            return jsonify({'success': False, 'message': 'Пароль должен содержать минимум 4 символа'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, что пароль не админский
        cursor.execute('SELECT role FROM auth_passwords WHERE id = ?', (password_id,))
        password_data = cursor.fetchone()
        
        if not password_data:
            conn.close()
            return jsonify({'success': False, 'message': 'Пароль не найден'}), 404
        
        if password_data['role'] == 'админ':
            conn.close()
            return jsonify({'success': False, 'message': 'Нельзя изменять админ пароль'}), 403
        
        # Проверяем, не существует ли уже такой пароль (кроме текущего)
        cursor.execute('SELECT id FROM auth_passwords WHERE password = ? AND id != ?', (new_password, password_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Такой пароль уже существует'}), 400
        
        cursor.execute('''
            UPDATE auth_passwords 
            SET password = ?, is_active = ?
            WHERE id = ?
        ''', (new_password, 1 if is_active else 0, password_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Пароль успешно обновлен'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/passwords/<int:password_id>', methods=['DELETE'])
@require_admin
def delete_password(password_id):
    """Удаление пароля"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, что пароль не админский
        cursor.execute('SELECT role FROM auth_passwords WHERE id = ?', (password_id,))
        password_data = cursor.fetchone()
        
        if not password_data:
            conn.close()
            return jsonify({'success': False, 'message': 'Пароль не найден'}), 404
        
        if password_data['role'] == 'админ':
            conn.close()
            return jsonify({'success': False, 'message': 'Нельзя удалять админ пароль'}), 403
        
        cursor.execute('DELETE FROM auth_passwords WHERE id = ?', (password_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Пароль успешно удален'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500




    

@app.route('/api/admin/logs')
@require_admin
def admin_logs_api():
    """API для получения логов с фильтрацией"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        status = request.args.get('status', '')
        role = request.args.get('role', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        offset = (page - 1) * limit
        
        # Строим запрос с фильтрами
        where_conditions = []
        params = []
        
        if status == 'success':
            where_conditions.append("success = 1")
        elif status == 'failed':
            where_conditions.append("success = 0")
            
        if role:
            where_conditions.append("role = ?")
            params.append(role)
            
        if date_from:
            where_conditions.append("DATE(login_time) >= ?")
            params.append(date_from)
            
        if date_to:
            where_conditions.append("DATE(login_time) <= ?")
            params.append(date_to)
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Получаем логи
        query = f"""
            SELECT password, role, ip_address, user_agent, login_time, success
            FROM login_logs
            {where_clause}
            ORDER BY login_time DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # Получаем общее количество для пагинации
        count_query = f"SELECT COUNT(*) FROM login_logs {where_clause}"
        count_params = params[:-2]  # Убираем limit и offset
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        conn.close()
        
        # Преобразуем в список словарей
        logs_list = []
        for log in logs:
            logs_list.append({
                'password': log['password'],
                'role': log['role'],
                'ip_address': log['ip_address'],
                'user_agent': log['user_agent'],
                'login_time': log['login_time'],
                'success': bool(log['success'])
            })
        
        total_pages = (total + limit - 1) // limit
        
        return jsonify({
            'success': True,
            'logs': logs_list,
            'total': total,
            'page': page,
            'pages': total_pages
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    
@app.route('/strategy')
def strategy_page():
    return render_template('strategy.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5010, debug=True)