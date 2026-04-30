"""Tests for pages/watchlist.py helpers (_is_stale, colour_verdict)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# _is_stale tests
# ---------------------------------------------------------------------------

def test_is_stale_returns_true_for_old_cache():
    """Cache fetched 3 hours ago should be stale when WATCHLIST_STALE_HOURS=2."""
    from pages.watchlist import _is_stale

    old_time = datetime.now(timezone.utc) - timedelta(hours=3)
    cache = {"fetched_at": old_time.isoformat()}

    with patch("pages.watchlist.WATCHLIST_STALE_HOURS", 2):
        assert _is_stale(cache) is True


def test_is_stale_returns_false_for_fresh_cache():
    """Cache fetched 1 hour ago should not be stale when WATCHLIST_STALE_HOURS=2."""
    from pages.watchlist import _is_stale

    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
    cache = {"fetched_at": recent_time.isoformat()}

    with patch("pages.watchlist.WATCHLIST_STALE_HOURS", 2):
        assert _is_stale(cache) is False


def test_is_stale_returns_true_for_missing_fetched_at():
    """Cache dict with no fetched_at key should always be considered stale."""
    from pages.watchlist import _is_stale

    cache = {"ohlcv": {}, "fundamentals": {}}
    assert _is_stale(cache) is True


# ---------------------------------------------------------------------------
# colour_verdict tests
# ---------------------------------------------------------------------------

def test_colour_verdict_buy_is_green():
    from pages.watchlist import colour_verdict

    assert "#d4edda" in colour_verdict("BUY")
    assert "#d4edda" in colour_verdict("Strong BUY")


def test_colour_verdict_sell_is_red():
    from pages.watchlist import colour_verdict

    assert "#f8d7da" in colour_verdict("SELL")
    assert "#f8d7da" in colour_verdict("Strong SELL")


def test_colour_verdict_hold_is_yellow():
    from pages.watchlist import colour_verdict

    assert "#fff3cd" in colour_verdict("HOLD")
