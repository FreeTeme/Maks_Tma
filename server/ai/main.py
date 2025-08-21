import pandas as pd
import numpy as np

PATH = "C:/Проекты/Maks_Tma/server/ai/btc_1d_data_2018_to_2025 (1).csv"  # путь к историческим данным

def load_ohlcv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={
        "open time": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume"
    })
    df["date"] = pd.to_datetime(df["date"].str.replace(" UTC", "", regex=False), errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return df

df = load_ohlcv(PATH)
df["vol_ma30"] = df["volume"].rolling(window=30, min_periods=1).mean()

def safe_div(numer, denom):
    return np.where(denom == 0, 0.0, numer / denom)

hl_range = (df["high"] - df["low"]).astype(float)
body = safe_div((df["close"] - df["open"]).astype(float), hl_range)
upper_shadow = safe_div((df["high"] - np.maximum(df["open"], df["close"])).astype(float), hl_range)
lower_shadow = safe_div((np.minimum(df["open"], df["close"]) - df["low"]).astype(float), hl_range)
vol_rel = safe_div(df["volume"].astype(float), df["vol_ma30"].astype(float))

W_BODY, W_VOL, W_UP, W_LOW = 0.6, 0.25, 0.075, 0.075

features = pd.DataFrame({
    "date": df["date"],
    "body": body,
    "upper": upper_shadow,
    "lower": lower_shadow,
    "vol_rel": vol_rel,
    "close": df["close"].astype(float)
}).reset_index(drop=True)

def candle_distance(idx_a: int, idx_b: int) -> float:
    a = features.loc[idx_a, ["body", "vol_rel", "upper", "lower"]].values
    b = features.loc[idx_b, ["body", "vol_rel", "upper", "lower"]].values
    weights = np.array([W_BODY, W_VOL, W_UP, W_LOW])
    return float(np.sum(weights * np.abs(a - b)))

def find_similar_patterns(start_date: str, end_date: str,
                          max_threshold: float = 0.2,
                          years_back: int = 5):
    sdt = pd.to_datetime(start_date)
    edt = pd.to_datetime(end_date)
    mask = (features["date"] >= sdt) & (features["date"] <= edt)
    pat_idx = features.index[mask].tolist()
    if len(pat_idx) < 2:
        raise ValueError("Паттерн должен содержать минимум 2 свечи.")

    search_start = edt - pd.DateOffset(years=years_back)
    search_mask = (features["date"] >= search_start) & (features["date"] < sdt)
    search_indices = features.index[search_mask].tolist()

    N = len(pat_idx)
    matches, outcomes, matched_patterns = [], [], []

    for i in search_indices:
        j = i + N - 1
        if j >= len(features):
            break
        window_idx = list(range(i, i + N))
        dists = [candle_distance(pat_idx[k], window_idx[k]) for k in range(N)]
        if all(d <= max_threshold for d in dists):
            matches.append((i, j))
            matched_patterns.append(df.loc[window_idx, ["date", "open", "high", "low", "close", "volume"]].to_dict(orient="records"))
            next_idx = j + 1
            if next_idx < len(features):
                last_close = float(features.loc[j, "close"])
                next_close = float(features.loc[next_idx, "close"])
                pct = (next_close - last_close) / last_close * 100.0
                outcomes.append(pct)

    def bucket(p):
        if abs(p) < 1.0: return "Change <1%"
        if 1 <= p <= 3: return "Growth 1–3%"
        if 4 <= p <= 6: return "Growth 4–6%"
        if 7 <= p <= 10: return "Growth 7–10%"
        if -3 <= p <= -1: return "Drop 1–3%"
        if -6 <= p <= -4: return "Drop 4–6%"
        if -10 <= p <= -7: return "Drop 7–10%"
        if p > 10: return "Growth >10%"
        if p < -10: return "Drop >10%"
        return "Other (1–10% gaps)"


    stat_counts = {}
    for p in outcomes:
        k = bucket(p)
        stat_counts[k] = stat_counts.get(k, 0) + 1
    stat_perc = {k: round(v * 100.0 / len(outcomes), 2) for k, v in stat_counts.items()} if outcomes else {}

    return {
        "pattern_len": N,
        "pattern_start": str(features.loc[pat_idx[0], "date"].date()),
        "pattern_end": str(features.loc[pat_idx[-1], "date"].date()),
        "matches_found": len(matches),
        "distribution_counts": stat_counts,
        "distribution_percents": stat_perc,
        "matched_patterns": matched_patterns
    }
