from flask import Blueprint, request, jsonify
import pandas as pd
import time
from .main import (
    analyze_selected_pattern, 
    api_get_ohlcv_data,  # Используем новые API функции
    api_get_data_bounds,
    get_supported_symbols,
    normalize_symbol
)

# Создаем Blueprint для анализа паттернов
pattern_bp = Blueprint('pattern', __name__, url_prefix='/api/pattern')

# Упрощенный кэш
data_cache = {}
CACHE_TIMEOUT = 300  # 5 минут

@pattern_bp.route('/symbols', methods=['GET'])
def api_symbols():
    """Возвращает список поддерживаемых торговых пар"""
    try:
        result = get_supported_symbols()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@pattern_bp.route('/bounds', methods=['GET'])
def pattern_bounds():
    """Возвращает границы доступных данных"""
    try:
        timeframe = request.args.get('timeframe', '1d')
        symbol = request.args.get('symbol', 'BTCUSDT')
        result = api_get_data_bounds(timeframe, symbol)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@pattern_bp.route('/ohlcv', methods=['GET'])
def api_ohlcv():
    """Упрощенный эндпоинт для получения OHLCV данных"""
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        timeframe = request.args.get('timeframe', '1d')
        symbol = request.args.get('symbol', 'BTCUSDT')
        
        # Простой кэш
        cache_key = f"ohlcv_{symbol}_{timeframe}_{from_date}_{to_date}"
        
        if cache_key in data_cache:
            cached_data, timestamp = data_cache[cache_key]
            if time.time() - timestamp < CACHE_TIMEOUT:
                return jsonify(cached_data)
        
        result = api_get_ohlcv_data(from_date, to_date, timeframe, symbol)
        
        if result['success']:
            data_cache[cache_key] = (result, time.time())
            return jsonify(result)
        else:
            return jsonify({'success': False, 'message': result['message']}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@pattern_bp.route('/analyze', methods=['POST'])
def analyze_pattern():
    """Упрощенный анализ паттерна"""
    start_time = time.time()
    max_request_time = 120
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        required_fields = ['num_candles', 'candles']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        timeframe = data.get('timeframe', '1d')
        symbol = data.get('symbol', 'BTCUSDT')
        no_cache = data.get('no_cache', False)
        
        # Проверяем время выполнения запроса
        if time.time() - start_time > max_request_time:
            return jsonify({'success': False, 'message': 'Request timeout'}), 408
        
        # Простой кэш
        if not no_cache:
            pattern_hash = hash(str([c['open_time'] for c in data['candles']]))
            cache_key = f"analysis_{symbol}_{timeframe}_{pattern_hash}"
            
            if cache_key in data_cache:
                cached_result, timestamp = data_cache[cache_key]
                if time.time() - timestamp < CACHE_TIMEOUT:
                    return jsonify(cached_result)
        
        print(f"Начинаем анализ паттерна: {data['num_candles']} свечей, Пара: {symbol}, ТФ: {timeframe}")
        
        # Проверяем время выполнения перед началом анализа
        if time.time() - start_time > max_request_time:
            return jsonify({'success': False, 'message': 'Request timeout before analysis'}), 408
        
        result = analyze_selected_pattern(
            data['candles'], 
            data['num_candles'], 
            timeframe, 
            symbol, 
            no_cache=no_cache
        )
        
        # Проверяем время выполнения после анализа
        if time.time() - start_time > max_request_time:
            return jsonify({'success': False, 'message': 'Analysis timeout'}), 408
        
        if 'error' in result:
            return jsonify({'success': False, 'message': result['error']}), 500
        
        # Кэшируем результат
        if not no_cache:
            pattern_hash = hash(str([c['open_time'] for c in data['candles']]))
            cache_key = f"analysis_{symbol}_{timeframe}_{pattern_hash}"
            data_cache[cache_key] = (result, time.time())
        
        total_time = time.time() - start_time
        print(f"Анализ завершен за {total_time:.2f} секунд")
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@pattern_bp.route('/force_update', methods=['POST'])
def force_update():
    """Принудительное обновление данных"""
    try:
        symbol = request.args.get('symbol', 'BTCUSDT')
        
        # Очищаем кэш для этой пары
        keys_to_remove = [key for key in data_cache.keys() if symbol in key]
        for key in keys_to_remove:
            del data_cache[key]
            
        return jsonify({
            'success': True, 
            'message': f'Кэш очищен для {symbol}',
            'cleared_entries': len(keys_to_remove)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Убираем ненужные эндпоинты
# @pattern_bp.route('/update_status', methods=['GET']) - больше не нужен
# Функции get_data_freshness и force_data_refresh больше не используются