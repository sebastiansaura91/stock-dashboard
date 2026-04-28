import math
import numpy as np
import pandas as pd
import pandas_ta as ta
from scipy.signal import find_peaks

_INDICATOR_WEIGHTS = {
    "ema_20_50": 0.10,
    "ema_50_200": 0.10,
    "adx": 0.08,
    "rsi": 0.12,
    "macd": 0.10,
    "stoch": 0.08,
    "bbands": 0.07,
    "atr": 0.05,
    "obv": 0.10,
    "volume": 0.05,
    "pattern": 0.15,
}

_PATTERN_INFO = {
    "double_bottom":        ("Double Bottom",        "Two equal lows — typically signals a bullish reversal.", "High", "bullish"),
    "double_top":           ("Double Top",           "Two equal highs — typically signals a bearish reversal.", "High", "bearish"),
    "head_and_shoulders":   ("Head & Shoulders",     "Left shoulder, higher head, right shoulder — bearish reversal signal.", "High", "bearish"),
    "inverse_hns":          ("Inverse H&S",          "Inverted pattern — bullish reversal signal.", "High", "bullish"),
    "ascending_triangle":   ("Ascending Triangle",   "Rising lows with flat resistance — bullish continuation.", "Medium", "bullish"),
    "descending_triangle":  ("Descending Triangle",  "Falling highs with flat support — bearish continuation.", "Medium", "bearish"),
    "symmetrical_triangle": ("Symmetrical Triangle", "Converging highs and lows — breakout pending, direction unclear.", "Medium", "neutral"),
    "bull_flag":            ("Bull Flag",            "Tight consolidation after a strong uptrend — signals continuation higher.", "Medium", "bullish"),
    "bear_flag":            ("Bear Flag",            "Tight consolidation after a strong downtrend — signals continuation lower.", "Medium", "bearish"),
    "cup_and_handle":       ("Cup & Handle",         "U-shaped base then small pullback — bullish breakout setup.", "Medium", "bullish"),
}


def _signal_to_score(signal: int) -> float:
    return {1: 100.0, 0: 50.0, -1: 0.0}.get(signal, 50.0)


def _ohlcv_to_df(ohlcv: dict) -> pd.DataFrame:
    return pd.DataFrame({
        "open": ohlcv["open"],
        "high": ohlcv["high"],
        "low": ohlcv["low"],
        "close": ohlcv["close"],
        "volume": ohlcv["volume"],
    })


def detect_patterns(ohlcv: dict) -> list[dict]:
    close = np.array(ohlcv["close"])
    dates = ohlcv["dates"]
    n = len(close)
    patterns = []

    if n < 30:
        return patterns

    # Double bottom (60-day window, 2% tolerance)
    window = close[-60:] if n >= 60 else close
    dates_w = dates[-60:] if n >= 60 else dates
    troughs, _ = find_peaks(-window, distance=10)
    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        if abs(window[t1] - window[t2]) / window[t1] < 0.02 and (t2 - t1) >= 10:
            name, meaning, reliability, direction = _PATTERN_INFO["double_bottom"]
            patterns.append({
                "name": name,
                "detected_at": dates_w[t2] if t2 < len(dates_w) else dates[-1],
                "meaning": meaning,
                "reliability": reliability,
                "direction": direction,
            })

    # Double top
    peaks, _ = find_peaks(window, distance=10)
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if abs(window[p1] - window[p2]) / window[p1] < 0.02 and (p2 - p1) >= 10:
            name, meaning, reliability, direction = _PATTERN_INFO["double_top"]
            patterns.append({
                "name": name,
                "detected_at": dates_w[p2] if p2 < len(dates_w) else dates[-1],
                "meaning": meaning,
                "reliability": reliability,
                "direction": direction,
            })

    # Head & Shoulders (60-day window)
    if len(peaks) >= 3 and len(window) >= 60:
        p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
        left_sh, head, right_sh = window[p1], window[p2], window[p3]
        if head > left_sh and head > right_sh and abs(left_sh - right_sh) / head < 0.05:
            name, meaning, reliability, direction = _PATTERN_INFO["head_and_shoulders"]
            patterns.append({"name": name, "detected_at": dates_w[p3] if p3 < len(dates_w) else dates[-1],
                              "meaning": meaning, "reliability": reliability, "direction": direction})

    # Inverse Head & Shoulders (60-day window)
    if len(troughs) >= 3 and len(window) >= 60:
        t1, t2, t3 = troughs[-3], troughs[-2], troughs[-1]
        left_sh, head, right_sh = window[t1], window[t2], window[t3]
        if head < left_sh and head < right_sh and abs(left_sh - right_sh) / abs(head) < 0.05:
            name, meaning, reliability, direction = _PATTERN_INFO["inverse_hns"]
            patterns.append({"name": name, "detected_at": dates_w[t3] if t3 < len(dates_w) else dates[-1],
                              "meaning": meaning, "reliability": reliability, "direction": direction})

    # Ascending / Descending / Symmetrical Triangle (40-day window)
    if n >= 40:
        tri = close[-40:]
        tri_dates = dates[-40:]
        tri_peaks, _ = find_peaks(tri, distance=5)
        tri_troughs, _ = find_peaks(-np.array(tri), distance=5)
        if len(tri_peaks) >= 2 and len(tri_troughs) >= 2:
            peak_slope = (tri[tri_peaks[-1]] - tri[tri_peaks[-2]]) / max(tri[tri_peaks[-2]], 1e-9)
            trough_slope = (tri[tri_troughs[-1]] - tri[tri_troughs[-2]]) / max(abs(tri[tri_troughs[-2]]), 1e-9)
            if trough_slope > 0.01 and abs(peak_slope) < 0.01:
                name, meaning, reliability, direction = _PATTERN_INFO["ascending_triangle"]
                patterns.append({"name": name, "detected_at": tri_dates[-1], "meaning": meaning, "reliability": reliability, "direction": direction})
            elif peak_slope < -0.01 and abs(trough_slope) < 0.01:
                name, meaning, reliability, direction = _PATTERN_INFO["descending_triangle"]
                patterns.append({"name": name, "detected_at": tri_dates[-1], "meaning": meaning, "reliability": reliability, "direction": direction})
            elif peak_slope < -0.005 and trough_slope > 0.005:
                name, meaning, reliability, direction = _PATTERN_INFO["symmetrical_triangle"]
                patterns.append({"name": name, "detected_at": tri_dates[-1], "meaning": meaning, "reliability": reliability, "direction": direction})

    # Bull flag: flagpole = bars[-30:-10], consolidation = bars[-10:] (<=10 bars per spec)
    if n >= 30:
        flagpole = close[-30:-10]
        consolidation = close[-10:]
        uptrend = len(flagpole) > 1 and (flagpole[-1] - flagpole[0]) / flagpole[0] > 0.05
        tight = np.std(consolidation) / np.mean(consolidation) < 0.02
        if uptrend and tight and consolidation[-1] < consolidation[0]:
            name, meaning, reliability, direction = _PATTERN_INFO["bull_flag"]
            patterns.append({"name": name, "detected_at": dates[-1], "meaning": meaning, "reliability": reliability, "direction": direction})

    # Bear flag: flagpole = bars[-30:-10], consolidation = bars[-10:] (<=10 bars per spec)
    if n >= 30:
        flagpole = close[-30:-10]
        consolidation = close[-10:]
        downtrend = len(flagpole) > 1 and (flagpole[-1] - flagpole[0]) / flagpole[0] < -0.05
        tight = np.std(consolidation) / np.mean(consolidation) < 0.02
        if downtrend and tight and consolidation[-1] > consolidation[0]:
            name, meaning, reliability, direction = _PATTERN_INFO["bear_flag"]
            patterns.append({"name": name, "detected_at": dates[-1], "meaning": meaning, "reliability": reliability, "direction": direction})

    # Cup & Handle (90-day window)
    if n >= 90:
        cup = close[-90:-10]
        handle = close[-10:]
        mid_idx = len(cup) // 2
        left = cup[:mid_idx]
        right = cup[mid_idx:]
        if left and right and min(cup) < cup[0] * 0.95 and min(cup) < cup[-1] * 0.95:
            # U-shape: start and end near same level, dip in middle
            if abs(cup[0] - cup[-1]) / cup[0] < 0.05:
                handle_declining = handle[-1] < handle[0]
                if handle_declining:
                    name, meaning, reliability, direction = _PATTERN_INFO["cup_and_handle"]
                    patterns.append({"name": name, "detected_at": dates[-10], "meaning": meaning, "reliability": reliability, "direction": direction})

    return patterns


def compute_technical_score(ohlcv: dict) -> tuple[int, list[str], list[dict]]:
    close = ohlcv["close"]
    if len(close) < 20:
        return 50, ["Insufficient data for technical analysis"], []

    df = _ohlcv_to_df(ohlcv)
    signals = {}
    drivers = []

    # EMA 20/50
    ema20 = ta.ema(df["close"], length=20)
    ema50 = ta.ema(df["close"], length=50)
    if ema20 is not None and ema50 is not None and not ema20.empty and not ema50.empty:
        price = df["close"].iloc[-1]
        e20, e50 = ema20.iloc[-1], ema50.iloc[-1]
        if price > e20 > e50:
            signals["ema_20_50"] = 1
            drivers.append("Price above EMA 20 and EMA 50 (bullish)")
        elif price < e20 < e50:
            signals["ema_20_50"] = -1
            drivers.append("Price below EMA 20 and EMA 50 (bearish)")
        else:
            signals["ema_20_50"] = 0

    # EMA 50/200
    ema200 = ta.ema(df["close"], length=min(200, len(df)))
    if ema50 is not None and ema200 is not None and not ema50.empty and not ema200.empty:
        if ema50.iloc[-1] > ema200.iloc[-1]:
            signals["ema_50_200"] = 1
            drivers.append("Golden cross: EMA 50 above EMA 200")
        else:
            signals["ema_50_200"] = -1
            drivers.append("Death cross: EMA 50 below EMA 200")

    # RSI
    rsi = ta.rsi(df["close"], length=14)
    if rsi is not None and not rsi.empty:
        r = rsi.iloc[-1]
        if r < 40:
            signals["rsi"] = 1
            drivers.append(f"RSI {r:.0f} — oversold, room to run")
        elif r > 65:
            signals["rsi"] = -1
            drivers.append(f"RSI {r:.0f} — overbought")
        else:
            signals["rsi"] = 0
            drivers.append(f"RSI {r:.0f} — neutral")

    # MACD
    macd_df = ta.macd(df["close"])
    if macd_df is not None and not macd_df.empty:
        macd_line = macd_df.iloc[:, 0]
        signal_line = macd_df.iloc[:, 2]
        if not macd_line.empty and not signal_line.empty:
            if macd_line.iloc[-1] > signal_line.iloc[-1]:
                signals["macd"] = 1
                drivers.append("MACD bullish crossover")
            else:
                signals["macd"] = -1
                drivers.append("MACD bearish crossover")

    # OBV trend
    obv = ta.obv(df["close"], df["volume"])
    if obv is not None and len(obv) >= 10:
        signals["obv"] = 1 if obv.iloc[-1] > obv.iloc[-10] else -1

    # Volume
    avg_vol = df["volume"].rolling(20).mean().iloc[-1]
    curr_vol = df["volume"].iloc[-1]
    price_up = df["close"].iloc[-1] > df["close"].iloc[-2]
    if curr_vol > avg_vol * 1.5:
        signals["volume"] = 1 if price_up else -1
    else:
        signals["volume"] = 0

    # Bollinger Bands
    bb = ta.bbands(df["close"])
    if bb is not None and not bb.empty:
        lower = bb.iloc[:, 0].iloc[-1]
        upper = bb.iloc[:, 2].iloc[-1]
        price = df["close"].iloc[-1]
        if price <= lower:
            signals["bbands"] = 1
        elif price >= upper:
            signals["bbands"] = -1
        else:
            signals["bbands"] = 0

    # Stochastic
    stoch = ta.stoch(df["high"], df["low"], df["close"])
    if stoch is not None and not stoch.empty and len(stoch) >= 2:
        k = stoch.iloc[:, 0]
        d = stoch.iloc[:, 1]
        if k.iloc[-1] < 30 and k.iloc[-1] > k.iloc[-2] and k.iloc[-1] > d.iloc[-1]:
            signals["stoch"] = 1
        elif k.iloc[-1] > 70 and k.iloc[-1] < k.iloc[-2] and k.iloc[-1] < d.iloc[-1]:
            signals["stoch"] = -1
        else:
            signals["stoch"] = 0

    # ADX
    adx = ta.adx(df["high"], df["low"], df["close"])
    if adx is not None and not adx.empty:
        adx_val = adx.iloc[:, 0].iloc[-1]
        dmp = adx.iloc[:, 1].iloc[-1]
        dmn = adx.iloc[:, 2].iloc[-1]
        if adx_val > 25:
            signals["adx"] = 1 if dmp > dmn else -1
        else:
            signals["adx"] = 0

    # ATR
    atr = ta.atr(df["high"], df["low"], df["close"])
    if atr is not None and not atr.empty:
        norm_atr = atr.iloc[-1] / df["close"].iloc[-1]
        signals["atr"] = 1 if norm_atr < 0.02 else -1

    # Patterns — sort by detected_at so most_recent is truly the latest by date
    patterns = detect_patterns(ohlcv)
    if patterns:
        most_recent = sorted(patterns, key=lambda p: p["detected_at"])[-1]
        signals["pattern"] = 1 if most_recent["direction"] == "bullish" else (-1 if most_recent["direction"] == "bearish" else 0)
        drivers.append(f"Pattern: {most_recent['name']} ({most_recent['direction']})")
    else:
        signals["pattern"] = 0

    total = sum(
        _signal_to_score(signals.get(k, 0)) * w
        for k, w in _INDICATOR_WEIGHTS.items()
    )
    score = int(math.floor(total))
    return max(0, min(100, score)), drivers, patterns
