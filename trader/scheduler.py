"""Background scheduler for periodic ticker data refresh.

Rewrite of the original Streamlit-dependent scheduler.
Uses a module-level singleton (threading.Lock, double-checked) instead of
st.session_state so it runs correctly inside FastAPI.
"""

import logging
import threading
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from cache import write_cache
from config import WATCHLIST_REFRESH_MINUTES
from data.fetcher import fetch_fundamentals, fetch_ohlcv
from data.finbert import classify_batch
from data.sentiment import fetch_all_sentiment

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()


def get_scheduler() -> BackgroundScheduler:
    """Return the shared BackgroundScheduler singleton (lazy init)."""
    global _scheduler
    if _scheduler is None:
        with _lock:
            if _scheduler is None:
                _scheduler = BackgroundScheduler(daemon=True)
    return _scheduler


# ---------------------------------------------------------------------------
# Core refresh logic (unchanged from original)
# ---------------------------------------------------------------------------

def refresh_ticker(ticker: str) -> None:
    """Fetch fresh data for *ticker* and write it to cache.

    All exceptions are caught so a transient error never crashes the thread.
    """
    try:
        ohlcv = fetch_ohlcv(ticker)
        fundamentals = fetch_fundamentals(ticker)
        sentiment_items = fetch_all_sentiment(ticker)

        unlabelled_indices = [
            i for i, item in enumerate(sentiment_items)
            if not item.get("label")
        ]
        if unlabelled_indices:
            headlines = [sentiment_items[i]["headline"] for i in unlabelled_indices]
            classifications = classify_batch(headlines)
            if len(classifications) != len(headlines):
                logger.warning(
                    "refresh_ticker: classify_batch length mismatch %d vs %d (%s)",
                    len(classifications), len(headlines), ticker,
                )
            for idx, classification in zip(unlabelled_indices, classifications):
                sentiment_items[idx]["label"] = classification["label"]
                sentiment_items[idx]["score"] = classification["score"]

        cache_data = {
            "ohlcv": ohlcv,
            "fundamentals": fundamentals,
            "sentiment_items": sentiment_items,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        write_cache(ticker, cache_data)
        logger.info("refresh_ticker: %s updated", ticker)
    except Exception:
        logger.exception("refresh_ticker: error refreshing %s", ticker)


def _refresh_all() -> None:
    """Job target: refresh every ticker currently in the watchlist."""
    from cache import get_watchlist_tickers
    for ticker in get_watchlist_tickers():
        refresh_ticker(ticker)


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------

def start_scheduler() -> None:
    """Start the singleton scheduler with a single watchlist-refresh job."""
    scheduler = get_scheduler()
    scheduler.add_job(
        func=_refresh_all,
        trigger=IntervalTrigger(minutes=WATCHLIST_REFRESH_MINUTES),
        id="refresh_all",
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()
        logger.info("start_scheduler: scheduler started")


def stop_scheduler() -> None:
    """Stop the scheduler (non-blocking)."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("stop_scheduler: scheduler stopped")


def refresh_ticker_now(ticker: str) -> None:
    """Synchronously refresh one ticker (on-demand from API)."""
    refresh_ticker(ticker)
