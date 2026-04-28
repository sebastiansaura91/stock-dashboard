import pytest
import pandas as pd
import numpy as np
from scoring.technical import compute_technical_score, detect_patterns


def make_ohlcv(n=120, trend="up"):
    base = 100.0
    close = [base + (i * 0.5 if trend == "up" else -i * 0.5) for i in range(n)]
    return {
        "dates": [f"2026-{i:04d}" for i in range(n)],
        "open": [c - 0.2 for c in close],
        "high": [c + 0.5 for c in close],
        "low": [c - 0.5 for c in close],
        "close": close,
        "volume": [1_000_000 + i * 1000 for i in range(n)],
    }


def test_technical_score_returns_int_in_range():
    ohlcv = make_ohlcv(n=120, trend="up")
    score, drivers, patterns = compute_technical_score(ohlcv)
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_uptrend_scores_higher_than_downtrend():
    up_score, _, _ = compute_technical_score(make_ohlcv(n=120, trend="up"))
    down_score, _, _ = compute_technical_score(make_ohlcv(n=120, trend="down"))
    assert up_score > down_score


def test_drivers_is_list_of_strings():
    _, drivers, _ = compute_technical_score(make_ohlcv())
    assert isinstance(drivers, list)
    assert all(isinstance(d, str) for d in drivers)


def test_patterns_is_list():
    _, _, patterns = compute_technical_score(make_ohlcv())
    assert isinstance(patterns, list)


def test_detect_patterns_returns_list():
    ohlcv = make_ohlcv(n=120)
    patterns = detect_patterns(ohlcv)
    assert isinstance(patterns, list)


def test_too_few_bars_returns_neutral_score():
    ohlcv = make_ohlcv(n=5)
    score, _, _ = compute_technical_score(ohlcv)
    assert score == 50
