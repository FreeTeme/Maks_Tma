import jupytext
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import os
import sys
from flask_cors import CORS
from ai.main import find_similar_patterns
from ai.main import df as ohlcv_df
from app.parser import staking_bp
import pandas as pd
import requests
import numpy as np
import time

# Add the server directory to Python path
server_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(server_dir)

app = Flask(__name__)
CORS(app)
app.secret_key = 'supersecretkey'
DATABASE = '../bot/referrals.db'

# Register the staking Blueprint
app.register_blueprint(staking_bp, url_prefix='/api')

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
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
def deduct_points():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not authenticated'}), 401

    try:
        data = request.get_json()
        points = int(data.get('points', 0))

        if points <= 0:
            return jupytext({'success': False, 'message': 'Invalid points value'}), 400

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
    user_id = request.args.get('user_id', '622077354')
    if user_id:
        session['user_id'] = user_id
        return redirect(url_for('profile'))
    return "Пожалуйста, укажите user_id в параметрах URL (?user_id=...)"

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
def chat():
    user_id = session.get('user_id', '622077354')
    chat_history = get_user_chat(user_id)
    return render_template('result.html', chat_history=chat_history)

@app.route('/submit_question', methods=['POST'])
def submit_question():
    user_id = session.get('user_id', '622077354')
    if not user_id:
        return redirect(url_for('index'))
    question = request.form.get('question')
    save_question(user_id, question)
    return redirect(url_for('chat'))


@app.route('/api/save_search', methods=['POST'])
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
def get_last_search():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not authenticated'}), 401

    last_search = session.get('last_staking_search')
    if last_search:
        return jsonify({'success': True, 'last_search': last_search})
    return jsonify({'success': False, 'message': 'No previous search found'})


@app.route('/chart')
def chart_route():
    return render_template('Chart.html')

@app.route('/staking')
def staking_route():
    return render_template('staking.html')

@app.route('/binance')
def binance_route():
    return render_template('binance.html')

@app.route('/bingx')
def bingx_route():
    return render_template('bingx.html')

@app.route('/bitget')
def bitget_route():
    return render_template('bitget.html')

@app.route('/bybit')
def bybit_route():
    return render_template('bybit.html')

# Аналитка паттернов , роутинг для нее
@app.route('/pattern')
def analysis():
    return render_template('pattern.html')

@app.route('/kucoin')
def kucoin_route():
    return render_template('kucoin.html')

@app.route('/okx')
def okx_route():
    return render_template('okx.html')

@app.route('/xtcom')
def xtcoin_route():
    return render_template('xtcom.html')


@app.route('/mexc')
def mexc_route():
    return render_template('mexc.html')


@app.route('/gateio')
def gateio_route():
    return render_template('gateio.html')

@app.route('/htx')
def htx_route():
    return render_template('htx.html')

@app.route('/bitmart')
def bitmart_route():
    return render_template('bitmart.html')


@app.route('/wallet')
def wallet_route():
    return render_template('wallet.html')

@app.route('/graf')
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


@app.route('/analyze_pattern', methods=['POST'])
def analyze_pattern():
    try:
        data = request.get_json()

        required_fields = ['num_candles', 'candles']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        candles = data['candles']
        start_date = candles[0]['open_time']
        end_date = candles[-1]['close_time']

        # Запуск анализа по живым данным с биржи (Binance 1D)
        try:
            result = analyze_with_live_data(start_date, end_date)
        except ValueError as ve:
            return jsonify({'success': False, 'message': str(ve)}), 400

        return jsonify({
            'success': True,
            'pattern_info': {
                'pattern_start': result['pattern_start'],
                'pattern_end': result['pattern_end'],
                'pattern_len': result['pattern_len']
            },
            'statistics': {
                'matches_found': result['matches_found'],
                'distribution_counts': result['distribution_counts'],
                'distribution_percents': result['distribution_percents']
            },
            'matched_patterns': result['matched_patterns']
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/pattern_bounds', methods=['GET'])
def pattern_bounds():
    try:
        start = str(ohlcv_df['date'].min().date())
        end = str(ohlcv_df['date'].max().date())
        return jsonify({'success': True, 'start': start, 'end': end})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ohlcv', methods=['GET'])
def api_ohlcv():
    try:
        start = request.args.get('from')
        end = request.args.get('to')
        source = request.args.get('source', 'csv')

        if source == 'binance':
            data = fetch_binance_ohlcv(start, end)
        else:
            data = ohlcv_df.copy()
            if start:
                data = data[data['date'] >= pd.to_datetime(start, errors='coerce')]
            if end:
                data = data[data['date'] <= pd.to_datetime(end, errors='coerce')]

        # Map to frontend schema
        records = []
        for _, r in data.iterrows():
            ot = pd.to_datetime(r['date'])
            ct = ot + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
            records.append({
                'open_time': ot.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'close_time': ct.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'open_price': float(r['open']),
                'close_price': float(r['close']),
                'high': float(r['high']),
                'low': float(r['low']),
                'volume': float(r['volume'])
            })
        return jsonify({'success': True, 'candles': records})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== Live OHLCV (Binance) and analysis helpers =====
def fetch_binance_ohlcv(start_date: str | None, end_date: str | None) -> pd.DataFrame:
    base = 'https://api.binance.com/api/v3/klines'
    symbol = 'BTCUSDT'
    interval = '1d'
    limit = 1000
    start_ts = int(pd.to_datetime(start_date if start_date else '2015-01-01').timestamp() * 1000)
    end_ts = int(pd.to_datetime(end_date if end_date else pd.Timestamp.utcnow().date()).timestamp() * 1000)

    rows = []
    cur = start_ts
    while cur <= end_ts:
        params = {'symbol': symbol, 'interval': interval, 'startTime': cur, 'endTime': end_ts, 'limit': limit}
        resp = requests.get(base, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        for k in data:
            # [ openTime, open, high, low, close, volume, closeTime, ... ]
            rows.append({
                'date': pd.to_datetime(k[0], unit='ms'),
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5]),
            })
        # next start is last closeTime + 1ms
        next_ts = data[-1][6] + 1
        if next_ts <= cur:
            break
        cur = next_ts
        time.sleep(0.2)

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=['date','open','high','low','close','volume'])
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df = df.sort_values('date').drop_duplicates(subset=['date']).reset_index(drop=True)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=['date','body','upper','lower','vol_rel','close'])
    df = df.copy()
    df['vol_ma30'] = df['volume'].rolling(window=30, min_periods=1).mean()
    def safe_div(n,d):
        return np.where(d == 0, 0.0, n/d)
    hl = (df['high'] - df['low']).astype(float)
    body = safe_div((df['close'] - df['open']).astype(float), hl)
    upper = safe_div((df['high'] - np.maximum(df['open'], df['close'])).astype(float), hl)
    lower = safe_div((np.minimum(df['open'], df['close']) - df['low']).astype(float), hl)
    vol_rel = safe_div(df['volume'].astype(float), df['vol_ma30'].astype(float))
    out = pd.DataFrame({
        'date': pd.to_datetime(df['date']).dt.tz_localize(None),
        'body': body,
        'upper': upper,
        'lower': lower,
        'vol_rel': vol_rel,
        'close': df['close'].astype(float)
    })
    return out.reset_index(drop=True)


def analyze_with_live_data(start_date: str, end_date: str,
                           max_threshold: float = 0.25, years_back: int = 6):
    # Normalize inputs to tz-naive
    sdt = pd.to_datetime(start_date, utc=True).tz_convert(None)
    edt = pd.to_datetime(end_date, utc=True).tz_convert(None)

    # Fetch live data for "years_back" before start and up to end
    start_fetch = (sdt - pd.DateOffset(years=years_back)).date().isoformat()
    end_fetch = edt.date().isoformat()
    df_live = fetch_binance_ohlcv(start_fetch, end_fetch)
    if df_live.empty:
        raise ValueError('Не удалось получить данные с биржи')

    feat = build_features(df_live)
    # find indices for pattern window
    mask = (feat['date'] >= sdt) & (feat['date'] <= edt)
    pat_idx = feat.index[mask].tolist()
    if len(pat_idx) < 2:
        raise ValueError('Паттерн должен содержать минимум 2 свечи в данных биржи')

    # search preceding windows
    search_mask = (feat['date'] < sdt)
    search_indices = feat.index[search_mask].tolist()
    N = len(pat_idx)

    def cdist(a,b):
        wa,wv,wup,wlo = 0.6,0.25,0.075,0.075
        A = feat.loc[a, ['body','vol_rel','upper','lower']].values
        B = feat.loc[b, ['body','vol_rel','upper','lower']].values
        w = np.array([wa,wv,wup,wlo])
        return float(np.sum(w * np.abs(A - B)))

    matches, outcomes, matched_patterns = [], [], []
    for i in search_indices:
        j = i + N - 1
        if j >= len(feat):
            break
        window_idx = list(range(i, i + N))
        dists = [cdist(pat_idx[k], window_idx[k]) for k in range(N)]
        if all(d <= max_threshold for d in dists):
            matches.append((i,j))
            matched_patterns.append(df_live.loc[window_idx, ['date','open','high','low','close','volume']].to_dict(orient='records'))
            next_idx = j + 1
            if next_idx < len(feat):
                last_close = float(feat.loc[j,'close'])
                next_close = float(feat.loc[next_idx,'close'])
                outcomes.append((next_close - last_close) / last_close * 100.0)

    def bucket(p):
        if abs(p) < 1.0: return 'Change <1%'
        if 1 <= p <= 3: return 'Growth 1–3%'
        if 4 <= p <= 6: return 'Growth 4–6%'
        if 7 <= p <= 10: return 'Growth 7–10%'
        if -3 <= p <= -1: return 'Drop 1–3%'
        if -6 <= p <= -4: return 'Drop 4–6%'
        if -10 <= p <= -7: return 'Drop 7–10%'
        if p > 10: return 'Growth >10%'
        if p < -10: return 'Drop >10%'
        return 'Other (1–10% gaps)'

    stat_counts = {}
    for p in outcomes:
        k = bucket(p)
        stat_counts[k] = stat_counts.get(k, 0) + 1
    stat_perc = {k: round(v * 100.0 / len(outcomes), 2) for k, v in stat_counts.items()} if outcomes else {}

    return {
        'pattern_len': N,
        'pattern_start': str(feat.loc[pat_idx[0], 'date'].date()),
        'pattern_end': str(feat.loc[pat_idx[-1], 'date'].date()),
        'matches_found': len(matches),
        'distribution_counts': stat_counts,
        'distribution_percents': stat_perc,
        'matched_patterns': matched_patterns
    }

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5010, debug=True)