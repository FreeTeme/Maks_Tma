import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
from typing import Dict, List, Tuple, Optional, Union

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
    '15m': '15m',
    '1h': '1h', 
    '4h': '4h',
    '1d': '1d',
    '1w': '1w'
}

def fetch_binance_ohlcv(start_date: str, end_date: str, timeframe: str = '1d') -> pd.DataFrame:
    """Загрузка данных OHLCV с Binance API с поддержкой разных таймфреймов"""
    base_url = 'https://api.binance.com/api/v3/klines'
    symbol = 'BTCUSDT'
    interval = TIMEFRAME_MAP.get(timeframe, '1d')
    limit = 1000
    
    start_ts = int(pd.to_datetime(start_date).timestamp() * 1000)
    end_ts = int(pd.to_datetime(end_date).timestamp() * 1000)
    
    rows = []
    current_ts = start_ts
    
    while current_ts <= end_ts:
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
                
            for kline in data:
                rows.append({
                    'date': pd.to_datetime(kline[0], unit='ms'),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'timeframe': timeframe
                })
                
            current_ts = data[-1][6] + 1
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Ошибка при загрузке данных: {e}")
            break
    
    df = pd.DataFrame(rows)
    if df.empty:
        return df
        
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df = df.sort_values('date').drop_duplicates(subset=['date']).reset_index(drop=True)
    return df

def get_full_historical_data(timeframe: str = '1d') -> pd.DataFrame:
    """Получение полных исторических данных для указанного таймфрейма"""
    try:
        # Определяем глубину данных в зависимости от таймфрейма
        if timeframe in ['15m', '1h']:
            # Для коротких таймфреймов берем меньше данных
            start_date = "2020-01-01"
        else:
            # Для дневных и недельных - больше данных
            start_date = "2017-01-01"
            
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"Загрузка исторических данных {timeframe} с {start_date} по {end_date}")
        df = fetch_binance_ohlcv(start_date, end_date, timeframe)
        
        print(f"Успешно загружено {len(df)} записей для таймфрейма {timeframe}")
        return df
        
    except Exception as e:
        print(f"Ошибка при загрузке исторических данных: {e}")
        return pd.DataFrame()

def build_features(df: pd.DataFrame, timeframe: str = '1d') -> pd.DataFrame:
    """Построение признаков для анализа свечных паттернов с учетом таймфрейма"""
    df = df.copy()
    
    # Адаптируем окно для медианного объема в зависимости от таймфрейма
    if timeframe == '15m':
        window_size = 96 * 7  # 7 дней для 15-минутных данных
    elif timeframe == '1h':
        window_size = 24 * 30  # 30 дней для часовых данных
    elif timeframe == '1d':
        window_size = 30  # 30 дней для дневных данных
    elif timeframe == '1w':
        window_size = 52  # 52 недели (1 год)
    else:
        window_size = 30
    
    # Вычисление медианного объема с адаптивным окном
    df['vol_median'] = df['volume'].rolling(window=window_size, min_periods=1, center=True).median()
    
    def safe_div(numer, denom):
        return np.where(denom == 0, 0.0, numer / denom)
    
    # Вычисление компонентов свечи
    hl_range = (df['high'] - df['low']).replace(0, 1e-12)
    
    body = safe_div((df['close'] - df['open']), hl_range)
    upper = safe_div((df['high'] - np.maximum(df['open'], df['close'])), hl_range)
    lower = safe_div((np.minimum(df['open'], df['close']) - df['low']), hl_range)
    vol_rel = safe_div(df['volume'], df['vol_median'])
    
    # Направление свечи
    direction = np.where(df['close'] > df['open'], 1.0, 
                        np.where(df['close'] < df['open'], -1.0, 0.0))
    
    # Создание DataFrame с признаками
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
    
    return features.dropna().reset_index(drop=True)

def candle_distance(features_df: pd.DataFrame, idx_a: int, idx_b: int) -> Tuple[float, str]:
    """Вычисление расстояния между двумя свечами"""
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

def find_similar_patterns(features_df: pd.DataFrame, ohlcv_df: pd.DataFrame, pattern_start_date: str, 
                         pattern_end_date: str, timeframe: str = '1d', max_threshold: float = SIMILAR_THRESHOLD,
                         years_back: int = 5) -> Dict:
    """Поиск похожих паттернов в исторических данных с учетом таймфрейма"""
    sdt = pd.to_datetime(pattern_start_date, errors="coerce")
    edt = pd.to_datetime(pattern_end_date, errors="coerce")
    
    if pd.isna(sdt) or pd.isna(edt):
        raise ValueError("Неверный формат даты")
    
    # Получаем индексы свечей в заданном диапазоне дат
    mask = (features_df['date'] >= sdt) & (features_df['date'] <= edt)
    pat_idx = features_df.index[mask].tolist()
    
    if len(pat_idx) < 2:
        raise ValueError("Паттерн должен содержать минимум 2 свечи")
    
    # Определяем дату начала поиска (адаптируем под таймфрейм)
    if timeframe in ['15m', '1h']:
        # Для коротких таймфреймов ищем меньше лет назад
        years_back = min(years_back, 2)
    
    search_start = edt - pd.DateOffset(years=years_back)
    search_mask = (features_df['date'] >= search_start) & (features_df['date'] < sdt)
    search_indices = features_df.index[search_mask].tolist()
    
    N = len(pat_idx)
    matches = []
    outcomes = []
    matched_patterns = []
    similarities = []
    price_changes = []
    
    # Поиск похожих паттернов
    for i in search_indices:
        j = i + N - 1
        if j >= len(features_df):
            continue
            
        window_idx = list(range(i, i + N))
        dists = []
        similarities_list = []
        valid_comparison = True
        
        for k in range(N):
            if pat_idx[k] >= len(features_df) or window_idx[k] >= len(features_df):
                valid_comparison = False
                break
                
            dist, similarity = candle_distance(features_df, pat_idx[k], window_idx[k])
            dists.append(dist)
            similarities_list.append(similarity)
            
            if dist > max_threshold:
                valid_comparison = False
                break
        
        if valid_comparison and all(d <= max_threshold for d in dists):
            matches.append((i, j))
            
            if all(s == "identical" for s in similarities_list):
                pattern_similarity = "identical"
            elif any(s == "similar" for s in similarities_list):
                pattern_similarity = "similar"
            else:
                pattern_similarity = "identical"
            
            similarities.append(pattern_similarity)
            
            # Сохраняем данные совпавшего паттерна
            pattern_data = []
            for idx in window_idx:
                candle_date = features_df.loc[idx, 'date']
                ohlcv_row = ohlcv_df[ohlcv_df['date'] == candle_date].iloc[0]
                
                pattern_data.append({
                    'date': candle_date,
                    'open': float(ohlcv_row['open']),
                    'high': float(ohlcv_row['high']),
                    'low': float(ohlcv_row['low']),
                    'close': float(ohlcv_row['close']),
                    'volume': float(ohlcv_row['volume']),
                    'direction': 'bullish' if features_df.loc[idx, 'direction'] > 0 else 'bearish',
                    'similarity': similarities_list[idx - i] if idx - i < len(similarities_list) else 'unknown',
                    'timeframe': timeframe
                })
            
            matched_patterns.append(pattern_data)
            
            # Вычисляем процентное изменение цены после паттерна
            pattern_end_date = features_df.loc[j, 'date']
            
            # Определяем временной интервал для следующей свечи в зависимости от таймфрейма
            if timeframe == '15m':
                delta = timedelta(minutes=15)
            elif timeframe == '1h':
                delta = timedelta(hours=1)
            elif timeframe == '1d':
                delta = timedelta(days=1)
            elif timeframe == '1w':
                delta = timedelta(weeks=1)
            else:
                delta = timedelta(days=1)
                
            next_date = pattern_end_date + delta

            # Ищем следующую свечу по дате
            next_candles = features_df[features_df['date'] >= next_date]

            if not next_candles.empty:
                next_candle = next_candles.iloc[0]
                next_close = float(next_candle['close'])
                last_close = float(features_df.loc[j, 'close'])
                pct_change = (next_close - last_close) / last_close * 100.0
                outcomes.append(pct_change)
                price_changes.append(pct_change)
    
    # Группировка результатов по категориям
    def bucket(pct):
        if abs(pct) < 1.0:
            return "Change <1%"
        if 1 <= pct <= 3:
            return "Growth 1–3%"
        if 4 <= pct <= 6:
            return "Growth 4–6%"
        if 7 <= pct <= 10:
            return "Growth 7–10%"
        if -3 <= pct <= -1:
            return "Drop 1–3%"
        if -6 <= pct <= -4:
            return "Drop 4–6%"
        if -10 <= pct <= -7:
            return "Drop 7–10%"
        if pct > 10:
            return "Growth >10%"
        if pct < -10:
            return "Drop >10%"
        return "Other"
    
    stat_counts = {}
    for pct in outcomes:
        category = bucket(pct)
        stat_counts[category] = stat_counts.get(category, 0) + 1
    
    stat_perc = {}
    if outcomes:
        total = len(outcomes)
        stat_perc = {k: round(v * 100.0 / total, 2) for k, v in stat_counts.items()}
    
    identical_count = sum(1 for s in similarities if s == "identical")
    similar_count = sum(1 for s in similarities if s == "similar")
    
    return {
        "pattern_len": N,
        "pattern_start": str(features_df.loc[pat_idx[0], 'date']),
        "pattern_end": str(features_df.loc[pat_idx[-1], 'date']),
        "timeframe": timeframe,
        "matches_found": len(matches),
        "identical_count": identical_count,
        "similar_count": similar_count,
        "distribution_counts": stat_counts,
        "distribution_percents": stat_perc,
        "matched_patterns": matched_patterns,
        "price_changes": price_changes
    }

def analyze_selected_pattern(selected_candles: List[Dict], num_candles: int, timeframe: str = '1d') -> Dict:
    """Анализ выбранного паттерна с поддержкой разных таймфреймов"""
    try:
        if not selected_candles or len(selected_candles) == 0:
            return {"error": "No candles selected for analysis"}
        
        # Получаем полные исторические данные для указанного таймфрейма
        ohlcv_df = get_full_historical_data(timeframe)
        if ohlcv_df.empty:
            return {"error": "Failed to load historical data"}
        
        # Строим признаки с указанием таймфрейма
        features_df = build_features(ohlcv_df, timeframe)
        
        # Правильно парсим даты для всех таймфреймов
        start_date = pd.to_datetime(selected_candles[0]['open_time']).strftime('%Y-%m-%d %H:%M:%S')
        end_date = pd.to_datetime(selected_candles[-1]['close_time']).strftime('%Y-%m-%d %H:%M:%S')
        
        # Ищем похожие паттерны с указанием таймфрейма
        result = find_similar_patterns(
            features_df,
            ohlcv_df,
            start_date,
            end_date,
            timeframe=timeframe,
            max_threshold=SIMILAR_THRESHOLD,
            years_back=8
        )
        
        return {
            'success': True,
            'pattern_info': {
                'pattern_start': result['pattern_start'],
                'pattern_end': result['pattern_end'],
                'pattern_len': result['pattern_len'],
                'timeframe': result['timeframe']
            },
            'statistics': {
                'matches_found': result['matches_found'],
                'distribution_counts': result['distribution_counts'],
                'distribution_percents': result['distribution_percents']
            },
            'matched_patterns': result['matched_patterns'],
            'price_changes': result['price_changes']
        }
        
    except Exception as e:
        return {"error": f"Analysis error: {str(e)}"}

def get_ohlcv_data(start_date: Optional[str] = None, end_date: Optional[str] = None, timeframe: str = '1d') -> Dict:
    """Получение данных OHLCV для указанного периода и таймфрейма"""
    try:
        # Получаем полные исторические данные для указанного таймфрейма
        df = get_full_historical_data(timeframe)
        if df.empty:
            return {"success": False, "message": "Failed to load historical data"}
        
        # Фильтруем по датам, если указаны
        if start_date:
            start_dt = pd.to_datetime(start_date)
            df = df[df['date'] >= start_dt]
        if end_date:
            end_dt = pd.to_datetime(end_date)
            df = df[df['date'] <= end_dt]
            
        # Преобразуем в нужный формат
        records = []
        for _, row in df.iterrows():
            open_time = row['date']
            
            # Определяем время закрытия в зависимости от таймфрейма
            if timeframe == '15m':
                close_time = open_time + timedelta(minutes=15) - timedelta(milliseconds=1)
                time_format = '%Y-%m-%dT%H:%M:%SZ'
            elif timeframe == '1h':
                close_time = open_time + timedelta(hours=1) - timedelta(milliseconds=1)
                time_format = '%Y-%m-%dT%H:%M:%SZ'
            elif timeframe == '1d':
                close_time = open_time + timedelta(days=1) - timedelta(milliseconds=1)
                time_format = '%Y-%m-%dT%H:%M:%SZ'
            elif timeframe == '1w':
                close_time = open_time + timedelta(weeks=1) - timedelta(milliseconds=1)
                time_format = '%Y-%m-%dT%H:%M:%SZ'
            else:
                close_time = open_time + timedelta(days=1) - timedelta(milliseconds=1)
                time_format = '%Y-%m-%dT%H:%M:%SZ'
            
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
    """Получение границ доступных данных для указанного таймфрейма"""
    try:
        df = get_full_historical_data(timeframe)
        if df.empty:
            today = datetime.now().date()
            if timeframe in ['15m', '1h']:
                start_date = (datetime.now() - timedelta(days=365)).date()
            else:
                start_date = (datetime.now() - timedelta(days=5*365)).date()
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

# Пример использования
if __name__ == "__main__":
    # Тестирование для разных таймфреймов
    timeframes = ['15m', '1h', '1d', '1w']
    
    for tf in timeframes:
        print(f"\n=== Тестирование таймфрейма {tf} ===")
        
        # Загрузка данных
        df = get_full_historical_data(tf)
        if df.empty:
            print(f"Не удалось загрузить данные для {tf}")
            continue
            
        features_df = build_features(df, tf)
        
        print(f"Загружено {len(df)} записей")
        print(f"Период: {df['date'].min()} - {df['date'].max()}")
        
        # Пример анализа паттерна (только для демонстрации)
        if len(df) > 10:
            try:
                # Берем последние 5 свечей как пример паттерна
                start_date = df.iloc[-5]['date'].strftime('%Y-%m-%d %H:%M:%S')
                end_date = df.iloc[-1]['date'].strftime('%Y-%m-%d %H:%M:%S')
                
                result = find_similar_patterns(
                    features_df,
                    df,
                    start_date,
                    end_date,
                    timeframe=tf,
                    max_threshold=SIMILAR_THRESHOLD,
                    years_back=1
                )
                
                print(f"Найдено совпадений: {result['matches_found']}")
                print(f"Идентичных паттернов: {result['identical_count']}")
                print(f"Похожих паттернов: {result['similar_count']}")
                
            except Exception as e:
                print(f"Ошибка анализа: {e}")