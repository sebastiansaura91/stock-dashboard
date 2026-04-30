"""Background scheduler for periodic ticker data refresh.

Uses APScheduler's BackgroundScheduler as a singleton stored in
st.session_state["_scheduler"].  One job per ticker fires every
WATCHLIST_REFRESH_MINUTES minutes.
"""

import logging
from datetime import datetime, timezone

import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from cache import write_cache
from config import WATCHLIST_REFRESH_MINUTES
from data.fetcher import fetch_fundamentals, fetch_ohlcv
from data.finbert import classify_batch
from data.sentiment import fetch_all_sentiment

logger = logging.getLogger(__name__)

_SESSION_KEY = "_scheduler"


# ---------------------------------------------------------------------------
# Core refresh logic
# ---------------------------------------------------------------------------

def refresh_ticker(ticker: str) -> None:
    """Fetch fresh data for *ticker* and write it to cache.

    All exceptions are caught and logged so that a transient network failure
    never crashes the background thread.
    """
    try:
        ohlcv = fetch_ohlcv(ticker)
        fundamentals = fetch_fundamentals(ticker)
        sentiment_items = fetch_all_sentiment(ticker)

        # Classify items that are missing a label (label is None or absent).
        unlabelled_indices = [
            i for i, item in enumerate(sentiment_items)
            if not item.get("label")
        ]
        if unlabelled_indices:
            headlines = [sentiment_items[i]["headline"] for i in unlabelled_indices]
            classifications = classify_batch(headlines)
            if len(classifications) != len(headlines):
                logger.warning(
                    "refresh_ticker: classify_batch returned %d results for %d headlines (%s)",
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
        logger.info("refresh_ticker: %s updated successfully", ticker)
    except Exception:  # noqa: BLE001
        logger.exception("refresh_ticker: error refreshing %s", ticker)


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------

def start_scheduler(tickers: list[str]) -> None:
    """Create (if necessary) and start the singleton BackgroundScheduler,
    adding one IntervalTrigger job per ticker.

    Safe to call multiple times — existing jobs are replaced, not duplicated,
    and the scheduler is only started once.
    """
    scheduler: BackgroundScheduler | None = st.session_state.get(_SESSION_KEY)

    # Create a fresh scheduler if none exists or the existing one is stopped.
    if scheduler is None or not scheduler.running:
        scheduler = BackgroundScheduler(daemon=True)
        st.session_state[_SESSION_KEY] = scheduler

    # APScheduler 3.x supports add_job before start(); jobs are queued and
    # begin firing only once the scheduler is running.
    for ticker in tickers:
        scheduler.add_job(
            func=refresh_ticker,
            trigger=IntervalTrigger(minutes=WATCHLIST_REFRESH_MINUTES),
            args=[ticker],
            id=f"refresh_{ticker}",
            replace_existing=True,
        )

    if not scheduler.running:
        scheduler.start()
        logger.info("start_scheduler: scheduler started with %d ticker(s)", len(tickers))


def stop_scheduler() -> None:
    """Stop the scheduler (if running) and remove it from session_state.

    Uses wait=False for a non-blocking shutdown.  Any in-progress refresh_ticker
    job may continue to run briefly after this returns; cache writes are still
    safe because write_cache is portalocker-guarded.
    """
    scheduler: BackgroundScheduler | None = st.session_state.get(_SESSION_KEY)
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("stop_scheduler: scheduler stopped")
    if _SESSION_KEY in st.session_state:
        del st.session_state[_SESSION_KEY]


# ---------------------------------------------------------------------------
# On-demand refresh
# ---------------------------------------------------------------------------

def refresh_ticker_now(ticker: str) -> None:
    """Synchronously refresh *ticker* (on-demand, called from the UI thread)."""
    refresh_ticker(ticker)
