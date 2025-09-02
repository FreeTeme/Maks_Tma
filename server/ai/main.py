import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Константы для весов признаков при сравнении свечей
W_BODY = 0.65     # Вес для тела свечи (разница между open и close)
W_VOL = 0.18      # Вес для относительного объема
W_UP = 0.085      # Вес для верхней тени
W_LOW = 0.085     # Вес для нижней тени

# Пороговые значения для классификации сходства свечей
IDENTICAL_THRESHOLD = 0.09    # Свечи идентичны
SIMILAR_THRESHOLD = 0.18      # Свечи похожи (допустимое отклонение)

def load_ohlcv(path: str) -> pd.DataFrame:
    """
    Загрузка и предобработка исторических данных OHLCV
    """
    # Шаг 1: Загрузка данных из CSV файла
    df = pd.read_csv(path)
    
    # Шаг 2: Нормализация названий колонок
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Шаг 3: Переименование колонок для единообразия
    df = df.rename(columns={
        "open time": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume"
    })
    
    # Шаг 4: Парсинг дат с обработкой временных зон
    dt = pd.to_datetime(df["date"].str.replace(" UTC", "", regex=False), errors="coerce", utc=True)
    df["date"] = pd.Series(dt).dt.tz_convert(None)
    
    # Шаг 5: Удаление строк с некорректными датами
    df = df.dropna(subset=["date"])
    
    # Шаг 6: Сортировка по дате и удаление дубликатов
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    
    return df

# Загрузка данных
PATH = "C:/Проекты/Maks_Tma/server/ai/btc_1d_data_2018_to_2025.csv"
df = load_ohlcv(PATH)

# Шаг 7: Вычисление скользящего среднего объема за 30 дней
df["vol_ma30"] = df["volume"].rolling(window=30, min_periods=1).mean()

def safe_div(numer, denom):
    """
    Безопасное деление с обработкой деления на ноль
    """
    return np.where(denom == 0, 0.0, numer / denom)

# Шаг 8: Вычисление компонентов свечи для анализа паттернов
hl_range = (df["high"] - df["low"]).astype(float)
hl_range = hl_range.replace(0, 1e-12)  # Избегаем деления на ноль

# Тело свечи (нормализованное к диапазону high-low)
body = safe_div((df["close"] - df["open"]).astype(float), hl_range)

# Направление свечи (1 - растущая, -1 - падающая, 0 - нейтральная)
direction = np.where(df["close"] > df["open"], 1.0, 
                    np.where(df["close"] < df["open"], -1.0, 0.0))

# Верхняя тень (нормализованная)
upper_shadow = safe_div((df["high"] - np.maximum(df["open"], df["close"])).astype(float), hl_range)

# Нижняя тень (нормализованная)
lower_shadow = safe_div((np.minimum(df["open"], df["close"]) - df["low"]).astype(float), hl_range)

# Относительный объем (по сравнению со скользящим средним)
vol_rel = safe_div(df["volume"].astype(float), df["vol_ma30"].astype(float))

# Шаг 9: Создание DataFrame с признаками для анализа
features = pd.DataFrame({
    "date": df["date"],          # Дата
    "body": body,                # Нормализованное тело свечи
    "direction": direction,      # Направление свечи (1, -1, 0) - оставлено для отображения
    "upper": upper_shadow,       # Нормализованная верхняя тени
    "lower": lower_shadow,       # Нормализованная нижняя тени
    "vol_rel": vol_rel,          # Относительный объем
    "close": df["close"].astype(float)  # Цена закрытия
}).reset_index(drop=True)

def candle_distance(idx_a: int, idx_b: int) -> float:
    """
    Вычисление расстояния между двумя свечами по их индексам
    Без учета направления свечи
    """
    try:
        # Получаем значения только для 4 признаков
        a = features.loc[idx_a, ["body", "vol_rel", "upper", "lower"]].values
        b = features.loc[idx_b, ["body", "vol_rel", "upper", "lower"]].values
        
        # Вычисляем разницы по каждому признаку
        body_diff = np.abs(a[0] - b[0])          # Разница по телу свечи
        vol_diff = np.abs(a[1] - b[1])           # Разница по объему
        upper_diff = np.abs(a[2] - b[2])         # Разница по верхней тени
        lower_diff = np.abs(a[3] - b[3])         # Разница по нижней тени
        
        # Применяем веса к разнице признаков
        weights = np.array([W_BODY, W_VOL, W_UP, W_LOW])
        diffs = np.array([body_diff, vol_diff, upper_diff, lower_diff])
        
        # Вычисляем взвешенное расстояние
        distance = float(np.sum(weights * diffs))
        
        # Классифицируем степень сходства
        if distance <= IDENTICAL_THRESHOLD:
            similarity = "identical"
        elif distance <= SIMILAR_THRESHOLD:
            similarity = "similar"
        else:
            similarity = "different"
        
        return distance, similarity
    
    except KeyError:
        # Если индексы выходят за границы, возвращаем большое расстояние
        return float('inf'), "different"

def find_similar_patterns(start_date: str, end_date: str,
                          max_threshold: float = SIMILAR_THRESHOLD,
                          years_back: int = 5):
    """
    Поиск похожих паттернов в исторических данных
    """
    # Преобразуем входные даты в datetime объекты
    sdt = pd.to_datetime(start_date, errors="coerce")
    edt = pd.to_datetime(end_date, errors="coerce")
    
    # Убеждаемся, что даты без временных зон
    if hasattr(sdt, "tzinfo") and sdt.tzinfo is not None:
        sdt = sdt.tz_convert(None)
    if hasattr(edt, "tzinfo") and edt.tzinfo is not None:
        edt = edt.tz_convert(None)
    
    # Получаем индексы свечей в заданном диапазоне дат
    dates = pd.to_datetime(features["date"], errors="coerce")
    mask = (dates >= sdt) & (dates <= edt)
    pat_idx = features.index[mask].tolist()
    
    # Проверяем, что паттерн содержит хотя бы 2 свечи
    if len(pat_idx) < 2:
        raise ValueError("Паттерн должен содержать минимум 2 свечи.")
    
    # Определяем дату начала поиска (years_back лет назад от конца паттерна)
    search_start = edt - pd.DateOffset(years=years_back)
    search_mask = (dates >= search_start) & (dates < sdt)
    search_indices = features.index[search_mask].tolist()
    
    # Количество свечей в паттерне
    N = len(pat_idx)
    
    # Списки для хранения результатов
    matches = []          # Индексы совпадений
    outcomes = []         # Процентные изменения после паттерна
    matched_patterns = []  # Данные совпавших паттернов
    similarities = []     # Степень сходства паттернов
    
    # Поиск похожих паттернов в исторических данных
    for i in search_indices:
        j = i + N - 1
        # Пропускаем, если выходим за границы данных
        if j >= len(features):
            continue
        
        # Получаем индексы окна для сравнения
        window_idx = list(range(i, i + N))
        
        # Вычисляем расстояния между соответствующими свечами
        dists = []
        similarities_list = []
        valid_comparison = True
        
        for k in range(N):
            # Проверяем, что оба индекса в пределах диапазона
            if pat_idx[k] >= len(features) or window_idx[k] >= len(features):
                valid_comparison = False
                break
                
            dist, similarity = candle_distance(pat_idx[k], window_idx[k])
            dists.append(dist)
            similarities_list.append(similarity)
            
            # Если расстояние превышает порог, прерываем проверку
            if dist > max_threshold:
                valid_comparison = False
                break
        
        # Если все расстояния в пределах порога, сохраняем совпадение
        if valid_comparison and all(d <= max_threshold for d in dists):
            matches.append((i, j))
            
            # Определяем общую степень сходства паттерна
            if all(s == "identical" for s in similarities_list):
                pattern_similarity = "identical"
            elif any(s == "similar" for s in similarities_list):
                pattern_similarity = "similar"
            else:
                pattern_similarity = "identical"  # Все свечи идентичны
            
            similarities.append(pattern_similarity)
            
            # Сохраняем данные совпавшего паттерна
            pattern_data = df.loc[window_idx, ["date", "open", "high", "low", "close", "volume"]].to_dict(orient="records")
            
            # Добавляем информацию о направлении каждой свечи (только для отображения)
            for idx, candle_data in enumerate(pattern_data):
                candle_idx = window_idx[idx]
                candle_data["direction"] = "bullish" if features.loc[candle_idx, "direction"] > 0 else "bearish"
                candle_data["similarity"] = similarities_list[idx]
            
            matched_patterns.append(pattern_data)
            
            # Вычисляем процентное изменение цены после паттерна
            next_idx = j + 1
            if next_idx < len(features):
                last_close = float(features.loc[j, "close"])
                next_close = float(features.loc[next_idx, "close"])
                pct = (next_close - last_close) / last_close * 100.0
                outcomes.append(pct)
    
    def bucket(p):
        """
        Группировка процентных изменений по категориям
        """
        if abs(p) < 1.0: 
            return "Change <1%"
        if 1 <= p <= 3: 
            return "Growth 1–3%"
        if 4 <= p <= 6: 
            return "Growth 4–6%"
        if 7 <= p <= 10: 
            return "Growth 7–10%"
        if -3 <= p <= -1: 
            return "Drop 1–3%"
        if -6 <= p <= -4: 
            return "Drop 4–6%"
        if -10 <= p <= -7: 
            return "Drop 7–10%"
        if p > 10: 
            return "Growth >10%"
        if p < -10: 
            return "Drop >10%"
        return "Other"
    
    # Статистика по результатам
    stat_counts = {}
    for p in outcomes:
        k = bucket(p)
        stat_counts[k] = stat_counts.get(k, 0) + 1
    
    # Процентное распределение
    stat_perc = {}
    if outcomes:
        total = len(outcomes)
        stat_perc = {k: round(v * 100.0 / total, 2) for k, v in stat_counts.items()}
    
    # Подсчет количества идентичных и похожих паттернов
    identical_count = sum(1 for s in similarities if s == "identical")
    similar_count = sum(1 for s in similarities if s == "similar")
    
    # Формирование результата
    return {
        "pattern_len": N,
        "pattern_start": str(dates.loc[pat_idx[0]].date()),
        "pattern_end": str(dates.loc[pat_idx[-1]].date()),
        "matches_found": len(matches),
        "identical_count": identical_count,
        "similar_count": similar_count,
        "distribution_counts": stat_counts,
        "distribution_percents": stat_perc,
        "matched_patterns": matched_patterns
    }

# Пример использования
if __name__ == "__main__":
    try:
        result = find_similar_patterns(
            start_date="2023-01-01",
            end_date="2023-01-07",
            max_threshold=SIMILAR_THRESHOLD,  # Используем порог для похожих свечей
            years_back=3
        )
        print(f"Найдено совпадений: {result['matches_found']}")
        print(f"Идентичных паттернов: {result['identical_count']}")
        print(f"Похожих паттернов: {result['similar_count']}")
        print(f"Распределение результатов: {result['distribution_percents']}")
        
        # Вывод информации о первых нескольких совпадениях
        for i, pattern in enumerate(result["matched_patterns"][:3]):
            print(f"\nСовпадение #{i+1}:")
            for candle in pattern:
                similarity_text = "идентична" if candle.get('similarity') == 'identical' else "похожа"
                print(f"  {candle['date'].date()}: {candle['direction']} свеча ({similarity_text}), Close: {candle['close']}")
                
    except Exception as e:
        print(f"Ошибка: {e}")