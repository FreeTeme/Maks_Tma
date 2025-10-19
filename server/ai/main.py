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

# Словарь для преобразования таймфреймов в интервалы Binance
TIMEFRAME_MAP = {
    '1h': '1h', 
    '4h': '4h',
    '1d': '1d',
    '1w': '1w'
}

# Глобальные кэши
_data_cache = {}
_features_cache = {}
_analysis_cache = {}

# Кэш для быстрых данных
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
    """Загружает данные из кэш"""
    try:
        cache_file = CACHE_DIR / f"{key}.pkl"
        if cache_file.exists():
            return pd.read_pickle(cache_file)
    except:
        pass
    return None

def fetch_binance_ohlcv_fast(start_date: str, end_date: str, timeframe: str = '1d') -> pd.DataFrame:
    """Быстрая загрузка данных OHLCV с Binance API"""
    cache_key = get_cache_key("ohlcv", timeframe, start_date, end_date)
    cached_data = load_from_cache(cache_key)
    if cached_data is not None:
        print(f"Используем кэшированные данные для {timeframe}")
        return cached_data
    
    base_url = 'https://api.binance.com/api/v3/klines'
    symbol = 'BTCUSDT'
    interval = TIMEFRAME_MAP.get(timeframe, '1d')
    limit = 1000
    
    start_ts = int(pd.to_datetime(start_date).timestamp() * 1000)
    end_ts = int(pd.to_datetime(end_date).timestamp() * 1000)
    
    all_rows = []
    current_ts = start_ts
    
    print(f"Загрузка данных {timeframe} с {start_date} по {end_date}")
    
    # Оптимизация: для недельных данных увеличиваем лимит
    if timeframe == '1w':
        limit = 2000
    
    request_count = 0
    while current_ts <= end_ts and request_count < 100:  # Защита от бесконечного цикла
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_ts,
            'endTime': end_ts,
            'limit': limit
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            # Быстрая обработка батча
            batch_rows = []
            for kline in data:
                batch_rows.append({
                    'date': pd.to_datetime(kline[0], unit='ms'),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'timeframe': timeframe
                })
            
            all_rows.extend(batch_rows)
            current_ts = data[-1][6] + 1
            request_count += 1
            
            print(f"Загружено {len(all_rows)} записей...")
            
            # Минимальная задержка только при необходимости
            if len(all_rows) > 50000:
                time.sleep(0.05)
                
        except Exception as e:
            print(f"Ошибка при загрузке данных: {e}")
            break
    
    df = pd.DataFrame(all_rows)
    if df.empty:
        return df
        
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df = df.sort_values('date').drop_duplicates(subset=['date']).reset_index(drop=True)
    
    print(f"Загрузка завершена. Всего записей: {len(df)}")
    print(f"Период данных: {df['date'].min()} - {df['date'].max()}")
    
    # Сохраняем в кэш
    save_to_cache(cache_key, df)
    
    return df

def get_full_historical_data(timeframe: str = '1d') -> pd.DataFrame:
    """Оптимизированное получение полных исторических данных"""
    # Проверяем кэш в памяти
    if timeframe in _data_cache:
        print(f"Используем кэшированные данные в памяти для {timeframe}")
        return _data_cache[timeframe].copy()
    
    # Проверяем кэш на диске
    cache_key = get_cache_key("full_data", timeframe)
    cached_data = load_from_cache(cache_key)
    if cached_data is not None:
        print(f"Используем кэшированные данные с диска для {timeframe}")
        _data_cache[timeframe] = cached_data
        return cached_data.copy()
    
    try:
        # Всегда загружаем с 2017 года по текущий день
        start_date = "2017-01-01"
        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        print(f"Загрузка полных данных {timeframe} с {start_date} по {end_date}")
        df = fetch_binance_ohlcv_fast(start_date, end_date, timeframe)
        
        if df.empty:
            print(f"Не удалось загрузить данные для {timeframe}")
            return pd.DataFrame()
            
        print(f"Успешно загружено {len(df)} записей для таймфрейма {timeframe}")
        print(f"Период данных: {df['date'].min()} - {df['date'].max()}")
        
        # Убедимся, что даты не имеют часового пояса
        df['date'] = df['date'].dt.tz_localize(None)
        
        # Проверяем, что данные охватывают нужный период
        data_start = df['date'].min()
        data_end = df['date'].max()
        expected_start = pd.to_datetime("2017-01-01")
        
        if data_start > expected_start:
            print(f"ВНИМАНИЕ: Данные начинаются с {data_start}, а не с 2017-01-01")
        
        # Сохраняем в кэши
        _data_cache[timeframe] = df.copy()
        save_to_cache(cache_key, df)
        
        return df
        
    except Exception as e:
        print(f"Ошибка при загрузке исторических данных: {e}")
        return pd.DataFrame()

def build_features_fast(df: pd.DataFrame, timeframe: str = '1d') -> pd.DataFrame:
    """Сверхбыстрое построение признаков"""
    cache_key = get_cache_key("features", timeframe, len(df))
    cached_features = load_from_cache(cache_key)
    if cached_features is not None:
        return cached_features
    
    df = df.copy()
    
    # Векторизованные вычисления для максимальной скорости
    hl_range = np.maximum(df['high'] - df['low'], 1e-12)
    
    # Быстрые вычисления компонентов
    body = (df['close'] - df['open']) / hl_range
    upper = (df['high'] - np.maximum(df['open'], df['close'])) / hl_range
    lower = (np.minimum(df['open'], df['close']) - df['low']) / hl_range
    
    # Упрощенное вычисление объема - используем глобальную медиану для скорости
    vol_median = df['volume'].median()
    vol_rel = df['volume'] / max(vol_median, 1)
    
    # Более точное вычисление направления (1 для бычьей, -1 для медвежьей, 0 для нейтральной)
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
        'timeframe': timeframe
    })
    
    # Сохраняем в кэш
    save_to_cache(cache_key, features)
    
    return features

def fast_pattern_distance_matrix(pattern_features, window_features):
    """Быстрое вычисление матрицы расстояний между паттерном и окнами"""
    # pattern_features: [N, 4] - признаки паттерна
    # window_features: [M, N, 4] - признаки окон
    
    # Векторизованное вычисление расстояний
    diffs = np.abs(window_features - pattern_features)
    weights = np.array([W_BODY, W_VOL, W_UP, W_LOW])
    
    # Суммируем взвешенные расстояния по всем признакам и свечам
    distances = np.sum(diffs * weights, axis=(1, 2))
    
    return distances

def calculate_price_changes_with_stats(matched_patterns, ohlcv_df, timeframe, candles_after=1):
    """
    Вычисление изменения цены с медианной статистикой
    
    Формула расчета для каждого паттерна:
    price_change = (close_next - close_pattern) / close_pattern * 100
    
    где:
    - close_pattern: цена закрытия последней свечи паттерна
    - close_next: цена закрытия следующей свечи после паттерна
    """
    price_changes = []
    directions = []  # Для статистики направлений
    
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
            # Берём свечу через N периодов после паттерна
            future_candle = future_candles.iloc[candles_after - 1]
            
            # Цена закрытия последней свечи паттерна
            pattern_close_price = last_pattern_candle['close']
            
            # Цена закрытия через N свечей после паттерна
            future_close_price = future_candle['close']
            
            # Процентное изменение по формуле: (новое - старое) / старое * 100
            price_change_pct = (future_close_price - pattern_close_price) / pattern_close_price * 100
            rounded_change = round(price_change_pct, 2)
            price_changes.append(rounded_change)
            
            # Определяем направление (1 = рост, -1 = падение, 0 = без изменений)
            if rounded_change > 0.1:  # Порог 0.1% чтобы избежать шума
                directions.append(1)
            elif rounded_change < -0.1:
                directions.append(-1)
            else:
                directions.append(0)
        else:
            # Если данных недостаточно, возвращаем 0
            price_changes.append(0.0)
            directions.append(0)
    
    # Медианная статистика
    stats = calculate_median_statistics(price_changes, directions)
    
    return price_changes, stats

def calculate_median_statistics(price_changes, directions):
    """
    Расчет медианной статистики по всем паттернам
    
    Формулы расчета:
    1. Медиана = серединное значение отсортированного массива
    2. Проценты = (количество_случаев / общее_количество) * 100
    3. Топ-20% медиана = медиана первых 20% отсортированных значений
    4. Нижние-20% медиана = медиана последних 20% отсортированных значений
    """
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
    
    # Фильтруем нули (паттерны без данных)
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
    
    # Основная медиана - серединное значение отсортированного массива
    median_change = float(np.median(valid_changes))
    
    # Статистика направлений
    total = len(valid_directions)
    bullish_count = sum(1 for d in valid_directions if d == 1)
    bearish_count = sum(1 for d in valid_directions if d == -1)
    neutral_count = sum(1 for d in valid_directions if d == 0)
    
    # Проценты по формуле: (количество / общее_количество) * 100
    bullish_percentage = round((bullish_count / total) * 100, 1) if total > 0 else 0
    bearish_percentage = round((bearish_count / total) * 100, 1) if total > 0 else 0
    neutral_percentage = round((neutral_count / total) * 100, 1) if total > 0 else 0
    
    # Медиана топ-20% лучших результатов
    sorted_changes = sorted(valid_changes, reverse=True)
    top_20_count = max(1, len(sorted_changes) // 5)  # 20%
    top_20_median = float(np.median(sorted_changes[:top_20_count]))
    
    # Медиана нижних-20% худших результатов
    bottom_20_count = max(1, len(sorted_changes) // 5)  # 20%
    bottom_20_median = float(np.median(sorted_changes[-bottom_20_count:]))
    
    # Success rate (процент паттернов с положительным исходом)
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

def find_similar_patterns_fast(features_df: pd.DataFrame, ohlcv_df: pd.DataFrame, 
                              pattern_start_date: str, pattern_end_date: str, 
                              timeframe: str = '1d', max_threshold: float = SIMILAR_THRESHOLD) -> Dict:
    """Ультрабыстрый поиск похожих паттернов с векторизацией"""
    sdt = pd.to_datetime(pattern_start_date, errors="coerce")
    edt = pd.to_datetime(pattern_end_date, errors="coerce")
    
    if pd.isna(sdt) or pd.isna(edt):
        raise ValueError("Неверный формат даты")
    
    # Получаем индексы свечей паттерна
    mask = (features_df['date'] >= sdt) & (features_df['date'] <= edt)
    pat_idx = features_df.index[mask].tolist()
    
    if len(pat_idx) < 2:
        raise ValueError("Паттерн должен содержать минимум 2 свечи")
    
    N = len(pat_idx)
    
    # Получаем матрицу признаков паттерна
    pattern_matrix = features_df.loc[pat_idx, ['body', 'vol_rel', 'upper', 'lower']].values
    
    # Ищем ВО ВСЕХ данных до начала паттерна
    search_mask = (features_df['date'] < sdt)
    search_indices = features_df.index[search_mask].tolist()
    
    print(f"Поиск паттернов в {len(search_indices)} возможных окнах...")
    
    # Подготавливаем данные для векторных вычислений
    feature_matrix = features_df[['body', 'vol_rel', 'upper', 'lower']].values
    
    matches = []
    matched_patterns = []
    
    # Ограничиваем количество проверяемых окон для скорости, но проверяем всю историю
    max_windows = min(1500, len(search_indices))  # Увеличили лимит
    step = max(1, len(search_indices) // max_windows)
    
    print(f"Проверяем {max_windows} окон с шагом {step}")
    
    # Собираем окна для проверка
    windows_to_check = []
    valid_indices = []
    
    for i in search_indices[::step]:
        j = i + N - 1
        if j < len(features_df):
            windows_to_check.append(feature_matrix[i:j+1])
            valid_indices.append(i)
    
    if windows_to_check:
        # Векторизованное вычисление расстояний для всех окон сразу
        windows_array = np.array(windows_to_check)
        distances = fast_pattern_distance_matrix(pattern_matrix, windows_array)
        
        # Находим совпадения
        for idx, distance in enumerate(distances):
            if distance <= max_threshold * N:  # Адаптивный порог
                i = valid_indices[idx]
                j = i + N - 1
                matches.append((i, j))
                
                # Сохраняем данные паттерна
                pattern_data = []
                for k in range(N):
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
                        'timeframe': timeframe
                    })
                
                matched_patterns.append(pattern_data)
    
    print(f"Найдено {len(matches)} совпадений")
    
    # Рассчитываем реальные изменения цены после паттернов с медианной статистикой
    price_changes, performance_stats = calculate_price_changes_with_stats(matched_patterns, ohlcv_df, timeframe, candles_after=1)
    
    # Упрощенная статистика для скорости
    stat_counts = {"Matches": len(matches)}
    stat_perc = {"Matches": 100.0} if matches else {}
    
    return {
        "pattern_len": N,
        "pattern_start": str(features_df.loc[pat_idx[0], 'date']),
        "pattern_end": str(features_df.loc[pat_idx[-1], 'date']),
        "timeframe": timeframe,
        "matches_found": len(matches),
        "identical_count": len(matches),
        "similar_count": 0,
        "distribution_counts": stat_counts,
        "distribution_percents": stat_perc,
        "matched_patterns": matched_patterns,
        "price_changes": price_changes,  # Теперь реальные данные, а не нули
        "performance_stats": performance_stats  # Медианная статистика
    }

def analyze_selected_pattern(selected_candles: List[Dict], num_candles: int, timeframe: str = '1d') -> Dict:
    """Оптимизированный анализ паттерна с кэшированием"""
    try:
        if not selected_candles or len(selected_candles) == 0:
            return {"error": "No candles selected for analysis"}
        
        # Проверяем соответствие количества свечей
        if len(selected_candles) != num_candles:
            return {"error": f"Number of candles mismatch: expected {num_candles}, got {len(selected_candles)}"}
        
        # Создаем ключ для кэша анализа
        pattern_hash = hash(tuple(
            (c['open_time'], c['close_price']) for c in selected_candles
        ))
        cache_key = get_cache_key("analysis", timeframe, pattern_hash)
        
        # Проверяем кэш анализа
        cached_result = load_from_cache(cache_key)
        if cached_result is not None:
            print("Используем кэшированный результат анализа")
            return cached_result
        
        print(f"Быстрый анализ паттерна: {len(selected_candles)} свечей, ТФ: {timeframe}")
        
        # Загружаем данные
        ohlcv_df = get_full_historical_data(timeframe)
        if ohlcv_df.empty:
            return {"error": "Failed to load historical data"}
        
        # Убедимся, что даты в ohlcv_df не имеют часового пояса
        ohlcv_df['date'] = ohlcv_df['date'].dt.tz_localize(None)
        
        # Строим признаки
        features_df = build_features_fast(ohlcv_df, timeframe)
        
        print(f"Загружено {len(ohlcv_df)} исторических свечей")
        print(f"Диапазон исторических данных: {ohlcv_df['date'].min()} - {ohlcv_df['date'].max()}")
        
        # Получаем даты выбранных свечей и преобразуем их к формату исторических данных
        selected_dates = []
        selected_directions = []  # Сохраняем направления выбранных свечей
        
        for candle in selected_candles:
            try:
                # Преобразуем open_time к тому же формату, что и в исторических данных
                open_time = pd.to_datetime(candle['open_time'])
                
                # Убираем часовой пояс, если он есть
                if open_time.tz is not None:
                    open_time = open_time.tz_localize(None)
                
                # Для дневных данных нормализуем до даты (без времени)
                if timeframe == '1d':
                    open_time = open_time.normalize()
                
                selected_dates.append(open_time)
                
                # Определяем направление выбранной свечи
                open_price = float(candle['open_price'])
                close_price = float(candle['close_price'])
                direction = 1 if close_price > open_price else (-1 if close_price < open_price else 0)
                selected_directions.append(direction)
                
                print(f"Выбранная свеча: {candle['open_time']} -> {open_time}, направление: {direction}")
            except Exception as e:
                print(f"Ошибка преобразования даты {candle['open_time']}: {e}")
                return {"error": f"Invalid date format: {candle['open_time']}"}
        
        # Находим индексы выбранных свечей в features_df
        pat_idx = []
        pattern_directions = []  # Сохраняем направления найденных свечей паттерна
        
        for selected_date, expected_direction in zip(selected_dates, selected_directions):
            # Ищем ближайшую дату в исторических данных
            time_diff = np.abs(features_df['date'] - selected_date)
            closest_idx = time_diff.idxmin()
            closest_date = features_df.loc[closest_idx, 'date']
            closest_diff = time_diff.loc[closest_idx]
            
            # Проверяем, что дата достаточно близкая (максимум 1 день разницы для дневных данных)
            max_diff = pd.Timedelta(days=1) if timeframe == '1d' else pd.Timedelta(hours=1)
            
            if closest_diff <= max_diff:
                # Проверяем направление свечи
                actual_direction = features_df.loc[closest_idx, 'direction']
                if abs(actual_direction - expected_direction) > 0.5:  # Допускаем небольшую погрешность
                    print(f"Направление не совпадает: ожидалось {expected_direction}, получено {actual_direction}")
                    return {"error": f"Direction mismatch for candle at {selected_date}"}
                
                pat_idx.append(closest_idx)
                pattern_directions.append(actual_direction)
                print(f"Найдена соответствущая свеча: {selected_date} -> {closest_date} (разница: {closest_diff}), направление: {actual_direction}")
            else:
                print(f"Не удалось найти близкую свечу для {selected_date}. Ближайшая: {closest_date} (разница: {closest_diff})")
                return {"error": f"Could not find matching candle for date {selected_date}"}
        
        if len(pat_idx) != num_candles:
            return {"error": f"Could not find all selected candles in historical data: found {len(pat_idx)}, expected {num_candles}"}
        
        # Сортируем индексы по порядку (они уже должны быть в правильном порядке)
        pat_idx.sort()
        
        print(f"Найден паттерн из {len(pat_idx)} свечей в исторических данных")
        print(f"Индексы паттерна: {pat_idx}")
        print(f"Направления паттерна: {pattern_directions}")
        
        # Получаем матрицу признаков паттерна
        pattern_matrix = features_df.loc[pat_idx, ['body', 'vol_rel', 'upper', 'lower']].values
        
        # Ищем ВО ВСЕХ данных до начала паттерна
        pattern_start_date = features_df.loc[pat_idx[0], 'date']
        search_mask = (features_df['date'] < pattern_start_date)
        search_indices = features_df.index[search_mask].tolist()
        
        print(f"Поиск паттернов в {len(search_indices)} возможных окнах...")
        
        # Подготавливаем данные для векторных вычислений
        feature_matrix = features_df[['body', 'vol_rel', 'upper', 'lower']].values
        direction_matrix = features_df['direction'].values
        
        matches = []
        matched_patterns = []
        
        # Ограничиваем количество проверяемых окон для скорости
        max_windows = min(1500, len(search_indices))
        step = max(1, len(search_indices) // max_windows)
        
        print(f"Проверяем {max_windows} окон с шагом {step}")
        
        # Собираем окна для проверки
        windows_to_check = []
        valid_indices = []
        
        for i in search_indices[::step]:
            j = i + num_candles - 1
            if j < len(features_df):
                windows_to_check.append(feature_matrix[i:j+1])
                valid_indices.append(i)
        
        if windows_to_check:
            # Векторизованное вычисление расстояний для всех окон сразу
            windows_array = np.array(windows_to_check)
            distances = fast_pattern_distance_matrix(pattern_matrix, windows_array)
            
            # Находим совпадения
            for idx, distance in enumerate(distances):
                if distance <= SIMILAR_THRESHOLD * num_candles:  # Адаптивный порог
                    i = valid_indices[idx]
                    j = i + num_candles - 1
                    
                    # Проверяем, что направления свечей совпадают с выбранным паттерном
                    candidate_directions = direction_matrix[i:j+1]
                    if not np.array_equal(pattern_directions, candidate_directions):
                        print(f"Пропускаем кандидата {i}-{j} из-за несовпадения направлений")
                        continue
                    
                    matches.append((i, j))
                    
                    # Сохраняем данные паттерна
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
                            'timeframe': timeframe
                        })
                    
                    matched_patterns.append(pattern_data)
                    print(f"Найден подходящий паттерн: {i}-{j} с расстоянием {distance}")
        
        print(f"Найдено {len(matches)} совпадений")
        
        # Рассчитываем реальные изменения цены после паттернов с медианной статистикой
        price_changes, performance_stats = calculate_price_changes_with_stats(matched_patterns, ohlcv_df, timeframe, candles_after=1)
        
        # Упрощенная статистика для скорости
        stat_counts = {"Matches": len(matches)}
        stat_perc = {"Matches": 100.0} if matches else {}
        
        response = {
            'success': True,
            'pattern_info': {
                'pattern_start': str(features_df.loc[pat_idx[0], 'date']),
                'pattern_end': str(features_df.loc[pat_idx[-1], 'date']),
                'pattern_len': num_candles,
                'timeframe': timeframe
            },
            'statistics': {
                'matches_found': len(matches),
                'distribution_counts': stat_counts,
                'distribution_percents': stat_perc
            },
            'matched_patterns': matched_patterns,
            'price_changes': price_changes,  # Теперь реальные данные, а не нули
            'performance_stats': performance_stats  # Медианная статистика
        }
        
        # Сохраняем в кэш
        save_to_cache(cache_key, response)
        
        return response
        
    except Exception as e:
        print(f"Ошибка быстрого анализа: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Analysis error: {str(e)}"}
    
# Сохраняем оригинальные функции для совместимости
def fetch_binance_ohlcv(start_date: str, end_date: str, timeframe: str = '1d') -> pd.DataFrame:
    return fetch_binance_ohlcv_fast(start_date, end_date, timeframe)

def build_features(df: pd.DataFrame, timeframe: str = '1d') -> pd.DataFrame:
    return build_features_fast(df, timeframe)

def find_similar_patterns(features_df: pd.DataFrame, ohlcv_df: pd.DataFrame, pattern_start_date: str, 
                         pattern_end_date: str, timeframe: str = '1d', max_threshold: float = SIMILAR_THRESHOLD,
                         years_back: int = 5) -> Dict:
    return find_similar_patterns_fast(features_df, ohlcv_df, pattern_start_date, pattern_end_date, timeframe, max_threshold)

def get_ohlcv_data(start_date: Optional[str] = None, end_date: Optional[str] = None, timeframe: str = '1d') -> Dict:
    """Оптимизированное получение данных OHLCV"""
    try:
        df = get_full_historical_data(timeframe)
        if df.empty:
            return {"success": False, "message": "Failed to load historical data"}
        
        if start_date:
            start_dt = pd.to_datetime(start_date)
            # Убираем часовой пояс для сравнения
            if start_dt.tz is not None:
                start_dt = start_dt.tz_localize(None)
            df = df[df['date'] >= start_dt]
        if end_date:
            end_dt = pd.to_datetime(end_date)
            # Убираем часовой пояс для сравнения
            if end_dt.tz is not None:
                end_dt = end_dt.tz_localize(None)
            df = df[df['date'] <= end_dt]
            
        records = []
        for _, row in df.iterrows():
            open_time = row['date']
            
            # Для всех таймфреймов используем одинаковый формат даты
            time_format = '%Y-%m-%dT%H:%M:%SZ'
            
            # Вычисляем close_time в зависимости от таймфрейма
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
                'timeframe': timeframe
            })
        
        return {
            "success": True, 
            "candles": records,
            "timeframe": timeframe,
            "total_candles": len(records)
        }
        
    except Exception as e:
        return {"success": False, "message": str(e)}

def get_data_bounds(timeframe: str = '1d') -> Dict:
    """Получение границ данных"""
    try:
        df = get_full_historical_data(timeframe)
        if df.empty:
            today = datetime.now().date()
            start_date = (datetime.now() - timedelta(days=365*8)).date()
            return {
                'success': True, 
                'start': str(start_date), 
                'end': str(today),
                'timeframe': timeframe
            }
        
        start = df['date'].min().date()
        end = df['date'].max().date()
        return {
            'success': True, 
            'start': str(start), 
            'end': str(end),
            'timeframe': timeframe
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}

# Оригинальная функция для совместимости
def candle_distance(features_df: pd.DataFrame, idx_a: int, idx_b: int) -> Tuple[float, str]:
    """Оригинальная функция для совместимости (не используется в быстром анализе)"""
    try:
        a = features_df.loc[idx_a, ['body', 'vol_rel', 'upper', 'lower']].values
        b = features_df.loc[idx_b, ['body', 'vol_rel', 'upper', 'lower']].values
        
        body_diff = np.abs(a[0] - b[0])
        vol_diff = np.abs(a[1] - b[1])
        upper_diff = np.abs(a[2] - b[2])
        lower_diff = np.abs(a[3] - b[3])
        
        weights = np.array([W_BODY, W_VOL, W_UP, W_LOW])
        diffs = np.array([body_diff, vol_diff, upper_diff, lower_diff])
        
        distance = float(np.sum(weights * diffs))
        
        if distance <= IDENTICAL_THRESHOLD:
            similarity = "identical"
        elif distance <= SIMILAR_THRESHOLD:
            similarity = "similar"
        else:
            similarity = "different"
        
        return distance, similarity
        
    except (KeyError, IndexError):
        return float('inf'), "different"

if __name__ == "__main__":
    # Тестирование загрузки данных
    timeframes = ['1d', '1h']
    
    for tf in timeframes:
        print(f"\n=== Тестирование загрузки данных {tf} ===")
        
        start_time = time.time()
        df = get_full_historical_data(tf)
        load_time = time.time() - start_time
        
        if df.empty:
            print(f"Не удалось загрузить данные для {tf}")
            continue
            
        start_time = time.time()
        features_df = build_features_fast(df, tf)
        features_time = time.time() - start_time
        
        print(f"Загружено {len(df)} записей за {load_time:.2f} сек")
        print(f"Признаки построены за {features_time:.2f} сек")
        print(f"Период данных: {df['date'].min()} - {df['date'].max()}")
        
        # Проверяем, что данные охватывают 2017-2025
        data_start = df['date'].min()
        data_end = df['date'].max()
        expected_start = pd.to_datetime("2017-01-01")
        expected_end = pd.to_datetime("2024-12-31")  # Текущий год
        
        if data_start <= expected_start:
            print("✓ Данные начинаются с 2017 года или ранее")
        else:
            print(f"✗ Данные начинаются с {data_start}, а не с 2017 года")
            
        if data_end >= expected_end:
            print("✓ Данные включают текущий год")
        else:
            print(f"✗ Данные заканчиваются на {data_end}, а не на текущий год")