"""Supabase-backed cache.

Keeps the same read_cache / write_cache interface as the original portalocker
implementation so all callers (scheduler, scoring/fundamental) work unchanged.
Adds watchlist CRUD: get_watchlist_tickers, add_watchlist_ticker,
remove_watchlist_ticker.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_client_instance = None


def _get_client():
    """Return a shared Supabase client (lazy singleton)."""
    global _client_instance
    if _client_instance is None:
        from config import SUPABASE_URL, SUPABASE_KEY
        from supabase import create_client
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY environment variables must be set."
            )
        _client_instance = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client_instance


# ---------------------------------------------------------------------------
# Ticker cache (replaces portalocker JSON files)
# ---------------------------------------------------------------------------

def read_cache(ticker: str, cache_dir=None) -> dict | None:
    """Return cached data for *ticker*, or None if not found.

    cache_dir is accepted for interface compatibility but ignored.
    """
    try:
        result = (
            _get_client()
            .table("tickers")
            .select("data")
            .eq("ticker", ticker.upper())
            .execute()
        )
        if result.data:
            return result.data[0]["data"]
        return None
    except Exception:
        logger.exception("read_cache(%s) failed", ticker)
        return None


def write_cache(ticker: str, data: dict, cache_dir=None) -> None:
    """Upsert *data* for *ticker* into the tickers table.

    cache_dir is accepted for interface compatibility but ignored.
    """
    try:
        _get_client().table("tickers").upsert(
            {
                "ticker": ticker.upper(),
                "data": data,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception:
        logger.exception("write_cache(%s) failed", ticker)


# ---------------------------------------------------------------------------
# Watchlist table
# ---------------------------------------------------------------------------

def get_watchlist_tickers() -> list[str]:
    """Return ordered list of watchlist tickers from Supabase."""
    try:
        result = (
            _get_client()
            .table("watchlist")
            .select("ticker")
            .execute()
        )
        return [row["ticker"] for row in (result.data or [])]
    except Exception:
        logger.exception("get_watchlist_tickers failed")
        from config import WATCHLIST
        return list(WATCHLIST)  # fallback to config default


def add_watchlist_ticker(ticker: str) -> None:
    """Add *ticker* to the watchlist (no-op if already present)."""
    try:
        _get_client().table("watchlist").insert(
            {"ticker": ticker.upper()}
        ).execute()
    except Exception:
        logger.exception("add_watchlist_ticker(%s) failed", ticker)


def remove_watchlist_ticker(ticker: str) -> None:
    """Remove *ticker* from the watchlist."""
    try:
        _get_client().table("watchlist").delete().eq(
            "ticker", ticker.upper()
        ).execute()
    except Exception:
        logger.exception("remove_watchlist_ticker(%s) failed", ticker)
