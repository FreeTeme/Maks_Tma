import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
from typing import Dict, List, Tuple, Optional, Union
import hashlib
from pathlib import Path

# Константы для весов признаков при сравнении свечей
W_BODY = 0.65
W_VOL = 0.18
W_UP = 0.085
W_LOW = 0.085

# Пороговые значения для классификации сходства свечей
IDENTICAL_THRESHOLD = 0.09
SIMILAR_THRESHOLD = 0.18

# Словарь для преобразования пар с # в формат Binance
SYMBOL_MAP = {
    'ETH#USDT': 'ETHUSDT',
    'BTC#USDT': 'BTCUSDT', 
    'XRP#USDT': 'XRPUSDT',
    'SOL#USDT': 'SOLUSDT',
    'BNB#USDT': 'BNBUSDT',
    'TRX#USDT': 'TRXUSDT',
    'ADA#USDT': 'ADAUSDT',
    'SUI#USDT': 'SUIUSDT',
    'LINK#USDT': 'LINKUSDT',
    'LTC#USDT': 'LTCUSDT',
    'TON#USDT': 'TONUSDT'
}

# Словарь для преобразования таймфреймов в интервалы Binance
TIMEFRAME_MAP = {
    '1h': '1h', 
    '4h': '4h',
    '1d': '1d',
    '1w': '1w'
}

def normalize_symbol(symbol: str) -> str:
    """Нормализует символ для Binance API"""
    return SYMBOL_MAP.get(symbol, symbol.replace('#', ''))

# Единый кэш для всех данных
CACHE_DIR = Path("pattern_cache")
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_key(*args):
    """Создает ключ для кэша из аргументов"""
    key_str = "_".join(str(arg) for arg in args)
    return hashlib.md5(key_str.encode()).hexdigest()

def save_to_cache(key, data):
    """Сохраняет данные в кэш"""
    try:
        cache_file = CACHE_DIR / f"{key}.pkl"
        pd.to_pickle(data, cache_file)
    except:
        pass

def load_from_cache(key):
    """Загружает данные из кэша"""
    try:
        cache_file = CACHE_DIR / f"{key}.pkl"
        if cache_file.exists():
            return pd.read_pickle(cache_file)
    except:
        pass
    return None

def fetch_binance_ohlcv_fast(start_date: str, end_date: str, timeframe: str = '1d', symbol: str = 'BTCUSDT') -> pd.DataFrame:
    """Быстрая загрузка данных OHLCV с Binance API для указанной пары"""
    normalized_symbol = normalize_symbol(symbol)
    cache_key = get_cache_key("ohlcv", normalized_symbol, timeframe, start_date, end_date)
    
    # Проверяем кэш
    cached_data = load_from_cache(cache_key)
    if cached_data is not None:
        return cached_data
    
    base_url = 'https://api.binance.com/api/v3/klines'
    interval = TIMEFRAME_MAP.get(timeframe, '1d')
    limit = 1000
    
    start_ts = int(pd.to_datetime(start_date).timestamp() * 1000)
    end_ts = int(pd.to_datetime(end_date).timestamp() * 1000)
    
    all_rows = []
    current_ts = start_ts
    
    print(f"Загрузка данных {normalized_symbol} {timeframe} с {start_date} по {end_date}")
    
    # Оптимизация: для недельных данных увеличиваем лимит
    if timeframe == '1w':
        limit = 2000
    
    while current_ts <= end_ts:
        params = {
            'symbol': normalized_symbol,
            'interval': interval,
            'startTime': current_ts,
            'endTime': end_ts,
            'limit': limit
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            for kline in data:
                all_rows.append({
                    'date': pd.to_datetime(kline[0], unit='ms'),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'timeframe': timeframe,
                    'symbol': normalized_symbol
                })
            
            if len(data) < limit:
                break
                
            current_ts = data[-1][6] + 1
            time.sleep(0.1)
                
        except Exception as e:
            print(f"Ошибка при загрузке данных для {normalized_symbol}: {e}")
            break
    
    if not all_rows:
        return pd.DataFrame()
        
    df = pd.DataFrame(all_rows)
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df = df.sort_values('date').drop_duplicates(subset=['date']).reset_index(drop=True)
    
    print(f"Загрузка завершена. Всего записей: {len(df)}")
    
    # Сохраняем в кэш
    save_to_cache(cache_key, df)
    
    return df

def get_ohlcv_data(timeframe: str = '1d', symbol: str = 'BTCUSDT') -> pd.DataFrame:
    """Упрощенное получение данных OHLCV"""
    normalized_symbol = normalize_symbol(symbol)
    
    # Проверяем кэш полных данных
    cache_key = get_cache_key("full_data", normalized_symbol, timeframe)
    cached_data = load_from_cache(cache_key)
    if cached_data is not None:
        return cached_data
    
    # Загружаем данные с 2017 года
    start_date = "2017-01-01"
    end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    df = fetch_binance_ohlcv_fast(start_date, end_date, timeframe, normalized_symbol)
    
    if not df.empty:
        df['date'] = df['date'].dt.tz_localize(None)
        save_to_cache(cache_key, df)
    
    return df

def build_features_fast(df: pd.DataFrame, timeframe: str = '1d') -> pd.DataFrame:
    """Сверхбыстрое построение признаков с правильным расчетом объема по ТЗ"""
    if df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    
    # Векторизованные вычисления для максимальной скорости
    hl_range = np.maximum(df['high'] - df['low'], 1e-12)
    
    # Быстрые вычисления компонентов
    body = (df['close'] - df['open']) / hl_range
    upper = (df['high'] - np.maximum(df['open'], df['close'])) / hl_range
    lower = (np.minimum(df['open'], df['close']) - df['low']) / hl_range
    
    # Расчет объема по ТЗ - скользящее среднее за 30 периодов
    vol_ma = df['volume'].rolling(window=30, min_periods=1).mean()
    vol_rel = df['volume'] / np.maximum(vol_ma, 1)
    
    # Направление (1 для бычьей, -1 для медвежьей, 0 для нейтральной)
    direction = np.where(df['close'] > df['open'], 1.0, 
                        np.where(df['close'] < df['open'], -1.0, 0.0))
    
    features = pd.DataFrame({
        'date': df['date'],
        'body': body,
        'upper': upper,
        'lower': lower,
        'vol_rel': vol_rel,
        'direction': direction,
        'close': df['close'],
        'timeframe': timeframe,
        'symbol': df.get('symbol', 'BTCUSDT')
    })
    
    return features

def calculate_single_candle_distance(candle_a, candle_b):
    """Расчет расстояния для одной свечи по ТЗ"""
    # candle_a и candle_b = [body, vol_rel, upper, lower]
    body_diff = abs(candle_a[0] - candle_b[0]) * W_BODY
    vol_diff = abs(candle_a[1] - candle_b[1]) * W_VOL
    upper_diff = abs(candle_a[2] - candle_b[2]) * W_UP
    lower_diff = abs(candle_a[3] - candle_b[3]) * W_LOW
    
    return body_diff + vol_diff + upper_diff + lower_diff

def compare_patterns_correct(pattern_features, candidate_features):
    """
    Сравнивает два паттерна по ТЗ:
    - Каждая свеча должна быть индивидуально проверена
    - Возвращает тип совпадения: "identical", "similar" или None
    """
    identical_count = 0
    similar_count = 0
    
    for i in range(len(pattern_features)):
        # Расчет расстояния для одной свечи
        candle_distance = calculate_single_candle_distance(
            pattern_features[i], candidate_features[i])
        
        if candle_distance <= IDENTICAL_THRESHOLD:
            identical_count += 1
        elif candle_distance <= SIMILAR_THRESHOLD:
            similar_count += 1
        else:
            return None, None  # Есть непохожая свеча - паттерн не подходит
    
    # Если все свечи прошли проверку
    if identical_count == len(pattern_features):
        return "identical", identical_count
    else:
        return "similar", identical_count + similar_count

def calculate_price_changes_with_stats(matched_patterns, ohlcv_df, timeframe, symbol='BTCUSDT', candles_after=1):
    """
    Вычисление изменения цены с медианной статистикой
    """
    price_changes = []
    directions = []
    
    for pattern in matched_patterns:
        if not pattern:
            price_changes.append(0.0)
            directions.append(0)
            continue
            
        # Последняя свеча паттерна
        last_pattern_candle = pattern[-1]
        pattern_end_date = last_pattern_candle['date']
        
        # Находим следующую свечу после паттерна
        future_candles = ohlcv_df[ohlcv_df['date'] > pattern_end_date]
        
        if len(future_candles) >= candles_after:
            future_candle = future_candles.iloc[candles_after - 1]
            
            pattern_close_price = last_pattern_candle['close']
            future_close_price = future_candle['close']
            
            price_change_pct = (future_close_price - pattern_close_price) / pattern_close_price * 100
            rounded_change = round(price_change_pct, 2)
            price_changes.append(rounded_change)
            
            if rounded_change > 0.1:
                directions.append(1)
            elif rounded_change < -0.1:
                directions.append(-1)
            else:
                directions.append(0)
        else:
            price_changes.append(0.0)
            directions.append(0)
    
    # Медианная статистика
    stats = calculate_median_statistics(price_changes, directions)
    
    return price_changes, stats

def calculate_median_statistics(price_changes, directions):
    """Расчет медианной статистики по всем паттернам"""
    if not price_changes:
        return {
            'median_change': 0,
            'bullish_percentage': 0,
            'bearish_percentage': 0,
            'neutral_percentage': 0,
            'top_20_percent_median': 0,
            'bottom_20_percent_median': 0,
            'success_rate': 0,
            'total_patterns': 0
        }
    
    # Фильтруем нули
    valid_changes = [ch for ch in price_changes if ch != 0]
    valid_directions = [dir for i, dir in enumerate(directions) if price_changes[i] != 0]
    
    if not valid_changes:
        return {
            'median_change': 0,
            'bullish_percentage': 0,
            'bearish_percentage': 0,
            'neutral_percentage': 0,
            'top_20_percent_median': 0,
            'bottom_20_percent_median': 0,
            'success_rate': 0,
            'total_patterns': len(price_changes)
        }
    
    median_change = float(np.median(valid_changes))
    
    # Статистика направлений
    total = len(valid_directions)
    bullish_count = sum(1 for d in valid_directions if d == 1)
    bearish_count = sum(1 for d in valid_directions if d == -1)
    neutral_count = sum(1 for d in valid_directions if d == 0)
    
    bullish_percentage = round((bullish_count / total) * 100, 1) if total > 0 else 0
    bearish_percentage = round((bearish_count / total) * 100, 1) if total > 0 else 0
    neutral_percentage = round((neutral_count / total) * 100, 1) if total > 0 else 0
    
    # Медиана топ-20% и нижних-20%
    sorted_changes = sorted(valid_changes, reverse=True)
    top_20_count = max(1, len(sorted_changes) // 5)
    top_20_median = float(np.median(sorted_changes[:top_20_count]))
    
    bottom_20_count = max(1, len(sorted_changes) // 5)
    bottom_20_median = float(np.median(sorted_changes[-bottom_20_count:]))
    
    success_rate = round((bullish_count / total) * 100, 1) if total > 0 else 0
    
    return {
        'median_change': round(median_change, 2),
        'bullish_percentage': bullish_percentage,
        'bearish_percentage': bearish_percentage,
        'neutral_percentage': neutral_percentage,
        'top_20_percent_median': round(top_20_median, 2),
        'bottom_20_percent_median': round(bottom_20_median, 2),
        'success_rate': success_rate,
        'total_patterns': len(price_changes),
        'valid_patterns': len(valid_changes)
    }

def analyze_selected_pattern(selected_candles: List[Dict], num_candles: int, timeframe: str = '1d', 
                           symbol: str = 'BTCUSDT', no_cache: bool = False) -> Dict:
    """Оптимизированный анализ паттерна с поддержкой разных пар"""
    normalized_symbol = normalize_symbol(symbol)
    
    try:
        if not selected_candles or len(selected_candles) != num_candles:
            return {"error": f"Number of candles mismatch: expected {num_candles}, got {len(selected_candles)}"}
        
        print(f"Анализ паттерна: {len(selected_candles)} свечей, Пара: {normalized_symbol}, ТФ: {timeframe}")
        
        # Загружаем исторические данные
        ohlcv_df = get_ohlcv_data(timeframe, normalized_symbol)
        if ohlcv_df.empty:
            return {"error": f"Failed to load historical data for {normalized_symbol}"}
        
        # Строим признаки
        features_df = build_features_fast(ohlcv_df, timeframe)
        
        # Получаем даты выбранных свечей
        selected_dates = []
        for candle in selected_candles:
            try:
                open_time = pd.to_datetime(candle['open_time'])
                if open_time.tz is not None:
                    open_time = open_time.tz_localize(None)
                if timeframe == '1d':
                    open_time = open_time.normalize()
                selected_dates.append(open_time)
            except Exception as e:
                return {"error": f"Invalid date format: {candle['open_time']}"}
        
        # Находим индексы выбранных свечей в features_df
        pat_idx = []
        for selected_date in selected_dates:
            time_diff = np.abs(features_df['date'] - selected_date)
            closest_idx = time_diff.idxmin()
            closest_date = features_df.loc[closest_idx, 'date']
            closest_diff = time_diff.loc[closest_idx]
            
            max_diff = pd.Timedelta(days=1) if timeframe == '1d' else pd.Timedelta(hours=1)
            if closest_diff <= max_diff:
                pat_idx.append(closest_idx)
            else:
                return {"error": f"Could not find matching candle for date {selected_date}"}
        
        if len(pat_idx) != num_candles:
            return {"error": f"Could not find all selected candles in historical data"}
        
        pat_idx.sort()
        
        # Получаем матрицу признаков паттерна
        pattern_matrix = features_df.loc[pat_idx, ['body', 'vol_rel', 'upper', 'lower']].values
        
        # Ищем ВО ВСЕХ данных до начала паттерна
        pattern_start_date = features_df.loc[pat_idx[0], 'date']
        search_mask = (features_df['date'] < pattern_start_date)
        search_indices = features_df.index[search_mask].tolist()
        
        feature_matrix = features_df[['body', 'vol_rel', 'upper', 'lower']].values
        
        identical_matches = []
        similar_matches = []
        matched_patterns = []
        
        # Ограничиваем количество проверяемых окон для скорости
        max_windows = min(1500, len(search_indices))
        step = max(1, len(search_indices) // max_windows)
        
        # Проверяем каждое окно-кандидат
        for i in search_indices[::step]:
            j = i + num_candles - 1
            if j >= len(features_df):
                continue
                
            candidate_features = feature_matrix[i:j+1]
            match_type, _ = compare_patterns_correct(pattern_matrix, candidate_features)
            
            if match_type == "identical":
                identical_matches.append((i, j))
            elif match_type == "similar":
                similar_matches.append((i, j))
        
        # Объединяем все совпадения
        all_matches = identical_matches + similar_matches
        
        # Сохраняем данные найденных паттернов
        for match in all_matches:
            i, j = match
            pattern_data = []
            for k in range(num_candles):
                candle_idx = i + k
                candle_date = features_df.loc[candle_idx, 'date']
                ohlcv_row = ohlcv_df[ohlcv_df['date'] == candle_date].iloc[0]
                
                pattern_data.append({
                    'date': candle_date,
                    'open': float(ohlcv_row['open']),
                    'high': float(ohlcv_row['high']),
                    'low': float(ohlcv_row['low']),
                    'close': float(ohlcv_row['close']),
                    'volume': float(ohlcv_row['volume']),
                    'direction': 'bullish' if features_df.loc[candle_idx, 'direction'] > 0 else 'bearish',
                    'timeframe': timeframe,
                    'symbol': normalized_symbol
                })
            
            matched_patterns.append(pattern_data)

        print(f"Найдено {len(all_matches)} совпадений (идентичных: {len(identical_matches)}, похожих: {len(similar_matches)})")
        
        # Рассчитываем изменения цены
        price_changes, performance_stats = calculate_price_changes_with_stats(matched_patterns, ohlcv_df, timeframe, normalized_symbol, candles_after=1)
        
        # Статистика
        stat_counts = {
            "Identical": len(identical_matches),
            "Similar": len(similar_matches),
            "Total": len(all_matches)
        }
        
        total_found = len(all_matches)
        stat_perc = {
            "Identical": round((len(identical_matches) / total_found * 100) if total_found > 0 else 0, 1),
            "Similar": round((len(similar_matches) / total_found * 100) if total_found > 0 else 0, 1),
            "Total": 100.0 if total_found > 0 else 0
        }
        
        return {
            'success': True,
            'pattern_info': {
                'pattern_start': str(features_df.loc[pat_idx[0], 'date']),
                'pattern_end': str(features_df.loc[pat_idx[-1], 'date']),
                'pattern_len': num_candles,
                'timeframe': timeframe,
                'symbol': normalized_symbol
            },
            'statistics': {
                'matches_found': len(all_matches),
                'identical_count': len(identical_matches),
                'similar_count': len(similar_matches),
                'distribution_counts': stat_counts,
                'distribution_percents': stat_perc
            },
            'matched_patterns': matched_patterns,
            'price_changes': price_changes,
            'performance_stats': performance_stats
        }
        
    except Exception as e:
        return {"error": f"Analysis error: {str(e)}"}

# API функции
def api_get_ohlcv_data(start_date: Optional[str] = None, end_date: Optional[str] = None, 
                   timeframe: str = '1d', symbol: str = 'BTCUSDT') -> Dict:
    """API функция для получения данных OHLCV"""
    normalized_symbol = normalize_symbol(symbol)
    try:
        df = get_ohlcv_data(timeframe, normalized_symbol)
        if df.empty:
            return {"success": False, "message": f"Failed to load data for {normalized_symbol}"}
        
        if start_date:
            start_dt = pd.to_datetime(start_date)
            if start_dt.tz is not None:
                start_dt = start_dt.tz_localize(None)
            df = df[df['date'] >= start_dt]
        if end_date:
            end_dt = pd.to_datetime(end_date)
            if end_dt.tz is not None:
                end_dt = end_dt.tz_localize(None)
            df = df[df['date'] <= end_dt]
            
        records = []
        for _, row in df.iterrows():
            open_time = row['date']
            
            time_format = '%Y-%m-%dT%H:%M:%SZ'
            
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
                'open_time': open_time.strftime(time_format),
                'close_time': close_time.strftime(time_format),
                'open_price': float(row['open']),
                'close_price': float(row['close']),
                'high': float(row['high']),
                'low': float(row['low']),
                'volume': float(row['volume']),
                'timeframe': timeframe,
                'symbol': normalized_symbol
            })
        
        return {
            "success": True, 
            "candles": records,
            "timeframe": timeframe,
            "symbol": normalized_symbol,
            "total_candles": len(records)
        }
        
    except Exception as e:
        return {"success": False, "message": str(e)}

def api_get_data_bounds(timeframe: str = '1d', symbol: str = 'BTCUSDT') -> Dict:
    """API функция для получения границ данных"""
    normalized_symbol = normalize_symbol(symbol)
    try:
        df = get_ohlcv_data(timeframe, normalized_symbol)
        if df.empty:
            today = datetime.now().date()
            start_date = (datetime.now() - timedelta(days=365*8)).date()
            return {
                'success': True, 
                'start': str(start_date), 
                'end': str(today),
                'timeframe': timeframe,
                'symbol': normalized_symbol
            }
        
        start = df['date'].min().date()
        end = df['date'].max().date()
        return {
            'success': True, 
            'start': str(start), 
            'end': str(end),
            'timeframe': timeframe,
            'symbol': normalized_symbol
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}

def get_supported_symbols() -> Dict:
    """Возвращает список поддерживаемых торговых пар"""
    return {
        "success": True,
        "symbols": list(SYMBOL_MAP.keys()),
        "binance_symbols": list(SYMBOL_MAP.values())
    }

# Функции для совместимости
def get_full_historical_data(timeframe: str = '1d', symbol: str = 'BTCUSDT') -> pd.DataFrame:
    return get_ohlcv_data(timeframe, symbol)

def fetch_binance_ohlcv(start_date: str, end_date: str, timeframe: str = '1d', symbol: str = 'BTCUSDT') -> pd.DataFrame:
    return fetch_binance_ohlcv_fast(start_date, end_date, timeframe, symbol)

def build_features(df: pd.DataFrame, timeframe: str = '1d') -> pd.DataFrame:
    return build_features_fast(df, timeframe)