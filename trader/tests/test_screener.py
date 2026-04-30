"""Tests for pages/screener.py helpers (_apply_filters, _load_universe)."""

import csv
import os
import tempfile
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# _apply_filters tests
# ---------------------------------------------------------------------------

ALL_VERDICTS = ["Strong BUY", "BUY", "HOLD", "SELL", "Strong SELL"]


def _make_result(final, verdict="BUY"):
    return {"ticker": "AAPL", "final": final, "verdict": verdict,
            "technical": 50, "fundamental": 50, "sentiment": 50}


def test_apply_filters_min_score():
    """Results with scores [80, 40, 60]; min_score=50 → only 80 and 60 returned."""
    from pages.screener import _apply_filters

    results = [
        _make_result(80),
        _make_result(40),
        _make_result(60),
    ]
    filtered = _apply_filters(results, min_score=50, verdict_filter=ALL_VERDICTS, max_results=10)
    finals = [r["final"] for r in filtered]
    assert 80 in finals
    assert 60 in finals
    assert 40 not in finals
    assert len(filtered) == 2


def test_apply_filters_verdict():
    """Filter only ['BUY'] → only BUY results returned."""
    from pages.screener import _apply_filters

    results = [
        {"ticker": "AAPL", "final": 80, "verdict": "BUY", "technical": 50, "fundamental": 50, "sentiment": 50},
        {"ticker": "MSFT", "final": 60, "verdict": "HOLD", "technical": 50, "fundamental": 50, "sentiment": 50},
        {"ticker": "NVDA", "final": 70, "verdict": "Strong BUY", "technical": 50, "fundamental": 50, "sentiment": 50},
    ]
    filtered = _apply_filters(results, min_score=0, verdict_filter=["BUY"], max_results=10)
    assert len(filtered) == 1
    assert filtered[0]["verdict"] == "BUY"


def test_apply_filters_sorted_descending():
    """Results should be returned in descending order of final score."""
    from pages.screener import _apply_filters

    results = [
        _make_result(60),
        _make_result(80),
        _make_result(70),
    ]
    filtered = _apply_filters(results, min_score=0, verdict_filter=ALL_VERDICTS, max_results=10)
    finals = [r["final"] for r in filtered]
    assert finals == sorted(finals, reverse=True)


def test_apply_filters_max_results():
    """10 results in; max_results=3 → only top 3 returned."""
    from pages.screener import _apply_filters

    results = [_make_result(score) for score in range(10, 110, 10)]  # 10 results: 10,20,...,100
    filtered = _apply_filters(results, min_score=0, verdict_filter=ALL_VERDICTS, max_results=3)
    assert len(filtered) == 3
    # Should be the top 3 scores: 100, 90, 80
    finals = [r["final"] for r in filtered]
    assert finals == [100, 90, 80]


def test_load_universe_reads_csv():
    """Write a temp CSV with a few tickers; assert _load_universe() returns the correct list."""
    from pages.screener import _load_universe

    tickers = ["AAPL", "MSFT", "NVDA", "GOOG"]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False,
                                     newline="", encoding="utf-8") as f:
        tmp_path = f.name
        writer = csv.DictWriter(f, fieldnames=["ticker"])
        writer.writeheader()
        for t in tickers:
            writer.writerow({"ticker": t})

    try:
        with patch("pages.screener.SCREENER_UNIVERSE", tmp_path):
            result = _load_universe()
        assert result == tickers
    finally:
        os.unlink(tmp_path)
