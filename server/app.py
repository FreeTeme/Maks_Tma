from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import os
import sys
from flask_cors import CORS
from app.parser import staking_bp

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
        
        # Проверяем наличие обязательных полей
        required_fields = ['num_candles', 'candles']
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        num_candles = data['num_candles']
        candles = data['candles']
        
        # Проверяем, что num_candles соответствует длине списка свечей
        if not isinstance(candles, list) or len(candles) != num_candles:
            return jsonify({'success': False, 'message': 'Invalid number of candles'}), 400
        
        # Проверяем каждую свечу на наличие требуемых полей
        candle_fields = [
            'open_time', 'close_time', 'open_price', 'close_price',
            'volume', 'low', 'high'
        ]
        for candle in candles:
            if not all(field in candle for field in candle_fields):
                return jsonify({'success': False, 'message': 'Invalid candle data'}), 400
        
        # Пока просто возвращаем подтверждение приема данных
        # Позже здесь добавим логику анализа на основе исторических данных и формул из ТЗ
        return jsonify({
            'success': True,
            'message': 'Pattern data received',
            'received_data': {
                'num_candles': num_candles,
                'candles': candles
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5010, debug=True)