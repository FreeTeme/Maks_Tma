from datetime import timedelta
from flask import Blueprint, request, jsonify
import pandas as pd
import time
from .main import (
    analyze_selected_pattern, 
    api_get_ohlcv_data,  
    api_get_data_bounds,
    get_supported_symbols,
    normalize_symbol,
    check_data_updates,        
    get_latest_ohlcv,
    check_data_freshness  
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

# pattern_blueprint.py - добавляем новые эндпоинты

# pattern_blueprint.py - обновите эндпоинты

@pattern_bp.route('/check_updates', methods=['GET'])
def check_updates():
    """Проверяет наличие новых данных без полной загрузки"""
    try:
        symbol = request.args.get('symbol', 'BTCUSDT')
        timeframe = request.args.get('timeframe', '1d')
        last_known = request.args.get('last_known')
        
        if not last_known:
            return jsonify({
                'success': False, 
                'message': 'last_known parameter is required'
            }), 400
        
        # Используем функцию из main.py
        result = check_data_updates(symbol, timeframe, last_known)
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        print(f"Error in check_updates: {str(e)}")  # Добавьте логирование
        return jsonify({
            'success': False, 
            'message': f'Error checking updates: {str(e)}'
        }), 500

@pattern_bp.route('/incremental_update', methods=['GET'])
def incremental_update():
    """Возвращает только новые данные с момента последнего обновления"""
    try:
        symbol = request.args.get('symbol', 'BTCUSDT')
        timeframe = request.args.get('timeframe', '1d')
        last_known = request.args.get('last_known')
        
        if not last_known:
            return jsonify({
                'success': False, 
                'message': 'last_known parameter is required'
            }), 400
        
        # Используем функцию из main.py
        new_data = get_latest_ohlcv(symbol, timeframe, last_known)
        
        if new_data.empty:
            return jsonify({
                'success': True, 
                'has_updates': False,
                'message': 'No new data available'
            })
        
        # Конвертируем в формат для фронтенда
        records = []
        for _, row in new_data.iterrows():
            open_time = row['date']
            
            # Определяем close_time в зависимости от таймфрейма
            if timeframe == '1h':
                close_time = open_time + timedelta(hours=1)
            elif timeframe == '4h':
                close_time = open_time + timedelta(hours=4)
            elif timeframe == '1d':
                close_time = open_time + timedelta(days=1)
            elif timeframe == '1w':
                close_time = open_time + timedelta(weeks=1)
            else:
                close_time = open_time + timedelta(days=1)
            
            records.append({
                'open_time': open_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'close_time': close_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'open_price': float(row['open']),
                'close_price': float(row['close']),
                'high': float(row['high']),
                'low': float(row['low']),
                'volume': float(row['volume']),
                'timeframe': timeframe,
                'symbol': symbol
            })
        
        # Получаем самую свежую дату для следующей проверки
        latest_timestamp = new_data['date'].max().strftime('%Y-%m-%dT%H:%M:%SZ')
        
        return jsonify({
            'success': True,
            'has_updates': True,
            'new_candles': records,
            'latest_timestamp': latest_timestamp,
            'retrieved_count': len(records),
            'symbol': symbol,
            'timeframe': timeframe
        })
        
    except Exception as e:
        print(f"Error in incremental_update: {str(e)}")  # Добавьте логирование
        return jsonify({
            'success': False, 
            'message': f'Error fetching incremental data: {str(e)}'
        }), 500
    
@pattern_bp.route('/force_refresh', methods=['POST'])
def force_refresh():
    """Принудительное обновление всех данных для символа"""
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol', 'BTCUSDT')
        timeframe = data.get('timeframe', '1d')
        
        normalized_symbol = normalize_symbol(symbol)
        
        # Очищаем кэш для этой пары
        keys_to_remove = [key for key in data_cache.keys() if normalized_symbol in key or symbol in key]
        for key in keys_to_remove:
            del data_cache[key]
        
        # Также очищаем файловый кэш
        from main import CACHE_DIR
        cache_patterns = [f"ohlcv_{normalized_symbol}", f"full_data_{normalized_symbol}"]
        for cache_file in CACHE_DIR.glob("*.pkl"):
            if any(pattern in cache_file.name for pattern in cache_patterns):
                try:
                    cache_file.unlink()
                except:
                    pass
        
        # Загружаем свежие данные
        from main import get_ohlcv_data
        fresh_data = get_ohlcv_data(timeframe, normalized_symbol)
        
        return jsonify({
            'success': True,
            'message': f'Data refreshed for {normalized_symbol}',
            'cleared_cache_entries': len(keys_to_remove),
            'fresh_data_count': len(fresh_data) if not fresh_data.empty else 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error refreshing data: {str(e)}'
        }), 500

@pattern_bp.route('/check_freshness', methods=['GET'])
def check_freshness():
    """Проверяет свежесть данных и при необходимости обновляет"""
    try:
        symbol = request.args.get('symbol', 'BTCUSDT')
        timeframe = request.args.get('timeframe', '1d')
        auto_update = request.args.get('auto_update', 'true').lower() == 'true'
        
        # Используем функцию из main.py
        freshness_check = check_data_freshness(symbol, timeframe)
        
        # Если данные устарели и auto_update=true, обновляем автоматически
        if auto_update and freshness_check.get('needs_update'):
            print(f"🔄 Автоматическое обновление данных для {symbol} {timeframe}")
            
            # Очищаем кэш
            from main import CACHE_DIR
            normalized_symbol = normalize_symbol(symbol)
            cache_patterns = [f"ohlcv_{normalized_symbol}", f"full_data_{normalized_symbol}"]
            cleared_count = 0
            
            for cache_file in CACHE_DIR.glob("*.pkl"):
                if any(pattern in cache_file.name for pattern in cache_patterns):
                    try:
                        cache_file.unlink()
                        cleared_count += 1
                        print(f"🗑️ Удален кэш: {cache_file.name}")
                    except Exception as e:
                        print(f"❌ Ошибка удаления кэша {cache_file.name}: {e}")
            
            # Загружаем свежие данные
            from main import get_ohlcv_data
            fresh_data = get_ohlcv_data(timeframe, symbol)
            
            freshness_check['auto_updated'] = True
            freshness_check['cleared_cache_entries'] = cleared_count
            freshness_check['fresh_data_count'] = len(fresh_data) if not fresh_data.empty else 0
            
            if not fresh_data.empty:
                latest_date = fresh_data['date'].max()
                freshness_check['new_latest_date'] = latest_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        return jsonify({
            'success': True,
            **freshness_check
        })
        
    except Exception as e:
        print(f"❌ Error in check_freshness: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error checking freshness: {str(e)}'
        }), 500
    
@pattern_bp.route('/force_data_refresh', methods=['POST'])
def force_data_refresh():
    """Принудительное обновление данных для символа"""
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol', 'BTCUSDT')
        timeframe = data.get('timeframe', '1d')
        
        normalized_symbol = normalize_symbol(symbol)
        
        # Очищаем кэш для этой пары
        from main import CACHE_DIR
        cache_patterns = [f"ohlcv_{normalized_symbol}", f"full_data_{normalized_symbol}"]
        cleared_count = 0
        
        for cache_file in CACHE_DIR.glob("*.pkl"):
            if any(pattern in cache_file.name for pattern in cache_patterns):
                try:
                    cache_file.unlink()
                    cleared_count += 1
                    print(f"🗑️ Удален кэш: {cache_file.name}")
                except Exception as e:
                    print(f"❌ Ошибка удаления кэша {cache_file.name}: {e}")
        
        # Загружаем свежие данные
        from main import get_ohlcv_data
        fresh_data = get_ohlcv_data(timeframe, normalized_symbol)
        
        return jsonify({
            'success': True,
            'message': f'Data refreshed for {normalized_symbol}',
            'cleared_cache_entries': cleared_count,
            'fresh_data_count': len(fresh_data) if not fresh_data.empty else 0,
            'latest_date': fresh_data['date'].max().strftime('%Y-%m-%dT%H:%M:%SZ') if not fresh_data.empty else 'No data'
        })
        
    except Exception as e:
        print(f"❌ Error in force_data_refresh: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error refreshing data: {str(e)}'
        }), 500