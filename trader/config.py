import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WATCHLIST = ["AAPL", "MSFT", "NVDA"]
SCREENER_UNIVERSE = os.path.join(BASE_DIR, "data", "sp500.csv")

WATCHLIST_REFRESH_MINUTES = 15
SCREENER_REFRESH_HOURS = 4
SCREENER_BATCH_SIZE = 50

DEFAULT_WEIGHTS = {"technical": 0.40, "fundamental": 0.35, "sentiment": 0.25}

# Verdict thresholds — adjust here to recalibrate all signals without touching engine.py
VERDICT_THRESHOLDS = {"strong_buy": 75, "buy": 60, "hold": 45, "sell": 30}

CACHE_DIR = os.path.join(BASE_DIR, "cache")
LOG_FILE = os.path.join(BASE_DIR, "logs", "trader.log")

SENTIMENT_LOOKBACK_HOURS = 48
SENTIMENT_HALF_LIFE_HOURS = 12
WATCHLIST_STALE_HOURS = 2
SCREENER_STALE_HOURS = 4
FINBERT_BATCH_SIZE = 16
