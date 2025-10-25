from flask import Blueprint, request, jsonify
import pandas as pd
import time
from functools import lru_cache
from .main import (
    analyze_selected_pattern, 
    get_ohlcv_data, 
    get_data_bounds, 
    get_data_freshness,
    get_full_historical_data,
    fetch_binance_ohlcv,
    build_features,
    find_similar_patterns,
    get_supported_symbols  # Добавляем импорт новой функции
)

# Создаем Blueprint для анализа паттернов
pattern_bp = Blueprint('pattern', __name__, url_prefix='/api/pattern')

# Глобальный кэш для данных
data_cache = {}
CACHE_TIMEOUT = 300  # 5 минут

# Добавляем новый эндпоинт для получения списка пар
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
        symbol = request.args.get('symbol', 'BTCUSDT')  # Добавляем параметр symbol
        result = get_data_bounds(timeframe, symbol)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'success': False, 'message': result['message']}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@pattern_bp.route('/ohlcv', methods=['GET'])
def api_ohlcv():
    """Оптимизированный эндпоинт с кэшированием"""
    try:
        source = request.args.get('source', 'binance')
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        timeframe = request.args.get('timeframe', '1d')
        symbol = request.args.get('symbol', 'BTCUSDT')  # Добавляем параметр symbol
        
        # Ключ для кэша теперь включает символ
        cache_key = f"{source}_{symbol}_{timeframe}_{from_date}_{to_date}"
        
        # Проверяем кэш
        if cache_key in data_cache:
            cached_data, timestamp = data_cache[cache_key]
            if time.time() - timestamp < CACHE_TIMEOUT:
                return jsonify(cached_data)
        
        if source == 'binance':
            result = get_ohlcv_data(from_date, to_date, timeframe, symbol)
            if result['success']:
                # Сохраняем в кэш
                data_cache[cache_key] = (result, time.time())
                return jsonify(result)
            else:
                return jsonify({'success': False, 'message': result['message']}), 500
        else:
            return jsonify({'success': False, 'message': 'Only binance source is supported'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@pattern_bp.route('/analyze', methods=['POST'])
def analyze_pattern():
    """Оптимизированный анализ с поддержкой разных пар"""
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
        symbol = data.get('symbol', 'BTCUSDT')  # Добавляем параметр symbol
        
        # Проверяем время выполнения запроса
        if time.time() - start_time > max_request_time:
            return jsonify({'success': False, 'message': 'Request timeout'}), 408
        
        # Проверяем, нужно ли отключить кэширование
        no_cache = data.get('no_cache', False)
        
        if not no_cache:
            # Создаем ключ для кэша на основе выбранных свечей и символа
            pattern_hash = hash(str([c['open_time'] for c in data['candles']]))
            cache_key = f"analysis_{symbol}_{timeframe}_{pattern_hash}"
            
            # Проверяем кэш
            if cache_key in data_cache:
                cached_result, timestamp = data_cache[cache_key]
                if time.time() - timestamp < CACHE_TIMEOUT:
                    print("Возвращаем кэшированный результат")
                    return jsonify(cached_result)
        
        print(f"Начинаем анализ паттерна: {data['num_candles']} свечей, Пара: {symbol}, ТФ: {timeframe}")
        
        # Проверяем время выполнения перед началом анализа
        if time.time() - start_time > max_request_time:
            return jsonify({'success': False, 'message': 'Request timeout before analysis'}), 408
        
        result = analyze_selected_pattern(data['candles'], data['num_candles'], timeframe, symbol, no_cache=no_cache)
        
        # Проверяем время выполнения после анализа
        if time.time() - start_time > max_request_time:
            return jsonify({'success': False, 'message': 'Analysis timeout'}), 408
        
        if 'error' in result:
            print(f"Ошибка анализа: {result['error']}")
            return jsonify({'success': False, 'message': result['error']}), 500
        
        # Кэшируем результат только если кэширование не отключено
        if not no_cache:
            pattern_hash = hash(str([c['open_time'] for c in data['candles']]))
            cache_key = f"analysis_{symbol}_{timeframe}_{pattern_hash}"
            data_cache[cache_key] = (result, time.time())
        
        total_time = time.time() - start_time
        print(f"Анализ завершен за {total_time:.2f} секунд")
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@pattern_bp.route('/update_status', methods=['GET'])
def get_update_status():
    """Возвращает статус фонового обновления"""
    timeframes = ['1h', '4h', '1d', '1w']
    symbol = request.args.get('symbol', 'BTCUSDT')  # Добавляем параметр symbol
    status = {}
    
    for tf in timeframes:
        freshness = get_data_freshness(tf, symbol)
        status[tf] = freshness
    
    return jsonify({
        'success': True,
        'data_status': status,
        'symbol': symbol
    })

@pattern_bp.route('/force_update', methods=['POST'])
def force_update():
    """Принудительное обновление данных для указанной пары"""
    try:
        symbol = request.args.get('symbol', 'BTCUSDT')  # Добавляем параметр symbol
        from .main import force_data_refresh
        
        # Обновляем все таймфреймы для выбранной пары
        timeframes = ['1h', '4h', '1d', '1w']
        results = {}
        
        for tf in timeframes:
            success = force_data_refresh(tf, symbol)
            results[tf] = success
            
        return jsonify({
            'success': True, 
            'message': f'Обновление данных для {symbol} запущено',
            'results': results
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500