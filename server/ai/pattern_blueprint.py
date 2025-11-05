from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
import pandas as pd
import time
from pathlib import Path
from ai.main import CACHE_DIR
from ai.main import (
    analyze_selected_pattern, 
    api_get_ohlcv_data,  
    api_get_data_bounds,
    get_supported_symbols,
    normalize_symbol,
    check_data_updates,        
    get_latest_ohlcv,
    check_data_freshness,
    get_ohlcv_data, 
    save_to_cache, 
    get_cache_key,
    fetch_binance_ohlcv_fast
)


# Создаем Blueprint для анализа паттернов
pattern_bp = Blueprint('pattern', __name__, url_prefix='/api/pattern')

CACHE_DIR = Path("pattern_cache")
CACHE_DIR.mkdir(exist_ok=True)
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
        
        print(f"📥 Запрос OHLCV: {symbol} {timeframe}")
        
        # Простой кэш
        cache_key = f"ohlcv_{symbol}_{timeframe}_{from_date}_{to_date}"
        
        if cache_key in data_cache:
            cached_data, timestamp = data_cache[cache_key]
            if time.time() - timestamp < CACHE_TIMEOUT:
                print(f"✅ Возвращаем кэшированные данные: {symbol} {timeframe}")
                return jsonify(cached_data)
        
        result = api_get_ohlcv_data(from_date, to_date, timeframe, symbol)
        
        if result['success']:
            data_cache[cache_key] = (result, time.time())
            print(f"✅ Загружены новые данные: {symbol} {timeframe} - {len(result.get('candles', []))} свечей")
            return jsonify(result)
        else:
            print(f"❌ Ошибка загрузки данных: {symbol} {timeframe} - {result.get('message')}")
            return jsonify({'success': False, 'message': result['message']}), 500
            
    except Exception as e:
        print(f"❌ Критическая ошибка в api_ohlcv: {str(e)}")
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
    """Альтернативный метод принудительного обновления данных"""
    try:
        symbol = request.args.get('symbol', 'BTCUSDT')
        timeframe = request.args.get('timeframe', '1d')
        
        print(f"🔄 Альтернативное обновление данных: {symbol}, {timeframe}")
        
        normalized_symbol = normalize_symbol(symbol)
        
        # Очищаем кэш
        cache_patterns = [f"ohlcv_{normalized_symbol}", f"full_data_{normalized_symbol}"]
        cleared_count = 0
        
        for cache_file in CACHE_DIR.glob("*.pkl"):
            if any(pattern in cache_file.name for pattern in cache_patterns):
                try:
                    cache_file.unlink()
                    cleared_count += 1
                except:
                    pass
        
        # Загружаем свежие данные
        fresh_data = get_ohlcv_data(timeframe, normalized_symbol)
        
        return jsonify({
            'success': True,
            'message': f'Data force updated for {normalized_symbol}',
            'cleared_cache_entries': cleared_count,
            'fresh_data_count': len(fresh_data) if not fresh_data.empty else 0
        })
        
    except Exception as e:
        print(f"❌ Ошибка в force_update: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error in force update: {str(e)}'
        }), 500

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
        cache_patterns = [f"ohlcv_{normalized_symbol}", f"full_data_{normalized_symbol}"]
        for cache_file in CACHE_DIR.glob("*.pkl"):
            if any(pattern in cache_file.name for pattern in cache_patterns):
                try:
                    cache_file.unlink()
                except:
                    pass
        
        # Загружаем свежие данные
        from ai.main import get_ohlcv_data
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
    
@pattern_bp.route('/refresh_data', methods=['POST'])
def refresh_data():
    """Надежное обновление данных - основной эндпоинт"""
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol', 'BTCUSDT')
        timeframe = data.get('timeframe', '1d')
        
        print(f"🔄 ЗАПУСК ОБНОВЛЕНИЯ ДАННЫХ: {symbol} {timeframe}")
        
        normalized_symbol = normalize_symbol(symbol)
        
        # 1. ОЧИСТКА КЭША
        cache_files = []
        patterns = [
            f"*ohlcv*{normalized_symbol}*",
            f"*full_data*{normalized_symbol}*", 
            f"*{normalized_symbol}*{timeframe}*"
        ]
        
        cleared_count = 0
        for pattern in patterns:
            for cache_file in CACHE_DIR.glob(pattern):
                if cache_file not in cache_files:
                    cache_files.append(cache_file)
        
        for cache_file in cache_files:
            try:
                if cache_file.exists():
                    cache_file.unlink()
                    cleared_count += 1
                    print(f"🗑️ Удален кэш: {cache_file.name}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить {cache_file.name}: {e}")
        
        print(f"✅ Очищено файлов кэша: {cleared_count}")
        
        # 2. ПЕРЕЗАГРУЗКА ДАННЫХ - ЗАГРУЖАЕМ С 2017 ГОДА

        
        # Загружаем данные с 2017 года
        start_date = "2017-01-01"
        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        print(f"📥 Загрузка данных с {start_date} по {end_date}")
        fresh_data = fetch_binance_ohlcv_fast(start_date, end_date, timeframe, normalized_symbol)
        
        if fresh_data.empty:
            print("❌ Не удалось загрузить данные с 2017 года, пробуем альтернативный метод...")
            # Пробуем загрузить с 2020 года как запасной вариант
            start_date = "2020-01-01"
            fresh_data = fetch_binance_ohlcv_fast(start_date, end_date, timeframe, normalized_symbol)
        
        print(f"✅ Загружено записей: {len(fresh_data)}")
        
        if not fresh_data.empty:
            latest_date = fresh_data['date'].max()
            earliest_date = fresh_data['date'].min()
            print(f"📅 Диапазон данных: {earliest_date} - {latest_date}")
            
            # Сохраняем в кэш
            cache_key = get_cache_key("full_data", normalized_symbol, timeframe)
            save_to_cache(cache_key, fresh_data)
            print("💾 Данные сохранены в кэш")
        
        return jsonify({
            'success': True,
            'message': f'Data successfully refreshed for {normalized_symbol}',
            'cleared_cache_entries': cleared_count,
            'fresh_data_count': len(fresh_data),
            'earliest_date': fresh_data['date'].min().strftime('%Y-%m-%dT%H:%M:%SZ') if not fresh_data.empty else 'No data',
            'latest_date': fresh_data['date'].max().strftime('%Y-%m-%dT%H:%M:%SZ') if not fresh_data.empty else 'No data',
            'data_loaded': not fresh_data.empty
        })
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА В refresh_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'Refresh failed: {str(e)}',
            'error_details': str(e)
        }), 500
    
@pattern_bp.route('/switch_data', methods=['POST'])
def switch_data():
    """Обновление данных при смене символа или таймфрейма"""
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol', 'BTCUSDT')
        timeframe = data.get('timeframe', '1d')
        
        print(f"🔄 ПЕРЕКЛЮЧЕНИЕ ДАННЫХ: {symbol}, ТФ: {timeframe}")
        
        normalized_symbol = normalize_symbol(symbol)
        
        # ОЧИСТКА КЭША ДЛЯ НОВЫХ ДАННЫХ
        cache_patterns = [
            f"*ohlcv*{normalized_symbol}*",
            f"*full_data*{normalized_symbol}*", 
            f"*{normalized_symbol}*{timeframe}*"
        ]
        
        cleared_count = 0
        for pattern in cache_patterns:
            for cache_file in CACHE_DIR.glob(pattern):
                try:
                    if cache_file.exists():
                        cache_file.unlink()
                        cleared_count += 1
                        print(f"🗑️ Удален кэш: {cache_file.name}")
                except Exception as e:
                    print(f"⚠️ Не удалось удалить {cache_file.name}: {e}")
        
        # ЗАГРУЗКА ДАННЫХ С 2017 ГОДА
        start_date = "2017-01-01"
        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        print(f"📥 Загрузка новых данных: {normalized_symbol} {timeframe} с {start_date} по {end_date}")
        
        fresh_data = fetch_binance_ohlcv_fast(start_date, end_date, timeframe, normalized_symbol)
        
        if fresh_data.empty:
            print("❌ Не удалось загрузить данные, пробуем альтернативный метод...")
            start_date = "2020-01-01"
            fresh_data = fetch_binance_ohlcv_fast(start_date, end_date, timeframe, normalized_symbol)
        
        print(f"✅ Загружено записей: {len(fresh_data)}")
        
        # ПОДГОТОВКА ДАННЫХ ДЛЯ ФРОНТЕНДА
        records = []
        if not fresh_data.empty:
            for _, row in fresh_data.iterrows():
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
            
            # Сохраняем в кэш
            cache_key = get_cache_key("full_data", normalized_symbol, timeframe)
            save_to_cache(cache_key, fresh_data)
            print("💾 Новые данные сохранены в кэш")
        
        return jsonify({
            'success': True,
            'message': f'Data switched to {normalized_symbol} {timeframe}',
            'candles': records,
            'candles_count': len(records),
            'earliest_date': fresh_data['date'].min().strftime('%Y-%m-%dT%H:%M:%SZ') if not fresh_data.empty else None,
            'latest_date': fresh_data['date'].max().strftime('%Y-%m-%dT%H:%M:%SZ') if not fresh_data.empty else None,
            'cleared_cache_entries': cleared_count
        })
        
    except Exception as e:
        print(f"❌ Ошибка переключения данных: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'Switch data failed: {str(e)}'
        }), 500
    
@pattern_bp.route('/ohlcv_fast', methods=['GET'])
def api_ohlcv_fast():
    """Быстрая загрузка OHLCV данных (только последние данные)"""
    try:
        timeframe = request.args.get('timeframe', '1d')
        symbol = request.args.get('symbol', 'BTCUSDT')
        
        print(f"⚡ БЫСТРАЯ загрузка: {symbol} {timeframe}")
        
        # Определяем период для быстрой загрузки
        end_date = datetime.now()
        
        if timeframe == '1h':
            start_date = end_date - timedelta(days=180)  # 6 месяцев
        elif timeframe == '4h':
            start_date = end_date - timedelta(days=360)  # 1 год
        else:
            start_date = end_date - timedelta(days=720)  # 2 года
        
        # Используем существующую функцию, но с ограниченным диапазоном
        result = api_get_ohlcv_data(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            timeframe=timeframe,
            symbol=symbol
        )
        
        if result['success']:
            print(f"✅ Быстрая загрузка: {symbol} {timeframe} - {len(result.get('candles', []))} свечей")
        else:
            print(f"❌ Ошибка быстрой загрузки: {symbol} {timeframe}")
            
        return jsonify(result)
            
    except Exception as e:
        print(f"❌ Критическая ошибка в api_ohlcv_fast: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500