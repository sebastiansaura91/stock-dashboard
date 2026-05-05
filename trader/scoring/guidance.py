"""Rule-based trade guidance.

Computes actionable entry range, target, and stop loss from
ATR, EMA levels, and the stock's verdict. No external data needed.

Risk philosophy:
  - BUY/Strong BUY: 2.5:1 reward-to-risk minimum
  - HOLD:          wait for pullback to EMA zone before entering
  - SELL/Strong SELL: exit guidance + stop for anyone still holding
"""

import pandas_ta as ta
import pandas as pd


def compute_guidance(ohlcv: dict, verdict: str, price: float) -> dict | None:
    """Return a guidance dict, or None if insufficient data."""
    closes = ohlcv.get("close", [])
    highs  = ohlcv.get("high", [])
    lows   = ohlcv.get("low", [])

    if len(closes) < 20 or price is None:
        return None

    df = pd.DataFrame({"close": closes, "high": highs, "low": lows})

    # --- ATR (14-period) ---
    atr_series = ta.atr(df["high"], df["low"], df["close"], length=14)
    atr = float(atr_series.iloc[-1]) if atr_series is not None and not atr_series.empty else price * 0.02

    # --- EMA 20 / 50 ---
    ema20_s = ta.ema(df["close"], length=20)
    ema50_s = ta.ema(df["close"], length=min(50, len(df)))
    ema20 = float(ema20_s.iloc[-1]) if ema20_s is not None and not ema20_s.empty else price
    ema50 = float(ema50_s.iloc[-1]) if ema50_s is not None and not ema50_s.empty else price

    def r(v: float) -> float:
        """Round to 2 decimal places."""
        return round(v, 2)

    v = verdict.lower()

    if "strong buy" in v:
        entry_low  = r(price)
        entry_high = r(price + 0.25 * atr)          # small leeway for limit orders
        target     = r(price + 2.5 * atr)
        stop       = r(price - 1.0 * atr)
        action     = "Buy now — strong momentum, enter at market."
        rationale  = (
            "Strong bullish conviction across technical, fundamental, and "
            "sentiment signals. Enter immediately; risk one ATR below entry."
        )

    elif "buy" in v:
        entry_low  = r(max(ema20, price - 0.75 * atr))
        entry_high = r(price)
        target     = r(price + 2.0 * atr)
        stop       = r(entry_low - 0.75 * atr)
        action     = "Buy on pullback — look for entry in the zone below."
        rationale  = (
            "Bullish bias confirmed. Waiting for a minor pullback to the entry "
            "zone improves risk/reward. Stop placed below EMA 20 support."
        )

    elif "hold" in v:
        entry_low  = r(min(ema20, ema50))
        entry_high = r(max(ema20, ema50))
        target     = r(price + 1.5 * atr)
        stop       = r(min(ema20, ema50) - 0.5 * atr)
        action     = "Hold existing position — wait for EMA pullback to add."
        rationale  = (
            "Mixed signals — no strong directional edge. If not yet invested, "
            "wait for price to pull back to the EMA zone before entering. "
            "Existing holders should stay with a tight stop below EMA 50."
        )

    elif "strong sell" in v:
        entry_low  = r(price - 0.5 * atr)   # re-used as "exit above this"
        entry_high = r(price)
        target     = r(price - 2.5 * atr)   # downside target
        stop       = r(price + 0.75 * atr)  # stop for short positions
        action     = "Exit immediately — bearish signal is strong."
        rationale  = (
            "Overwhelming bearish signals. Exit all long positions at market. "
            "Short sellers may target the level below; stop above current price."
        )

    else:  # SELL
        entry_low  = r(price - 0.5 * atr)
        entry_high = r(price)
        target     = r(price - 2.0 * atr)
        stop       = r(price + 0.75 * atr)
        action     = "Reduce or exit position — bearish bias."
        rationale  = (
            "Bearish signals outweigh bullish ones. Begin reducing exposure. "
            "Hold a stop above current price to limit losses if trend reverses."
        )

    rr = round(abs(target - price) / max(abs(price - stop), 0.01), 1)
    is_bullish = "buy" in v

    return {
        "action":       action,
        "rationale":    rationale,
        "entry_low":    entry_low,
        "entry_high":   entry_high,
        "target":       target,
        "stop_loss":    stop,
        "atr":          r(atr),
        "risk_reward":  rr,
        "is_bullish":   is_bullish,
    }
