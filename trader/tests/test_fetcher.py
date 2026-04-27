import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from data.fetcher import fetch_ohlcv, fetch_fundamentals


def make_mock_ticker(info=None, history=None):
    mock = MagicMock()
    mock.info = info or {
        "trailingPE": 28.4,
        "enterpriseToEbitda": 21.1,
        "revenueGrowth": 0.08,
        "grossMargins": 0.44,
        "operatingMargins": 0.30,
        "debtToEquity": 170.0,
        "sector": "Technology",
    }
    mock.history.return_value = history or pd.DataFrame({
        "Open": [170.0, 171.0],
        "High": [172.0, 173.0],
        "Low": [169.0, 170.0],
        "Close": [171.5, 172.0],
        "Volume": [50000000, 55000000],
    }, index=pd.to_datetime(["2026-04-24", "2026-04-25"]))
    return mock


@patch("data.fetcher.yf.Ticker")
def test_fetch_ohlcv_returns_correct_keys(mock_ticker_cls):
    mock_ticker_cls.return_value = make_mock_ticker()
    result = fetch_ohlcv("AAPL")
    assert "dates" in result
    assert "close" in result
    assert len(result["dates"]) == len(result["close"])


@patch("data.fetcher.yf.Ticker")
def test_fetch_fundamentals_maps_fields(mock_ticker_cls):
    mock_ticker_cls.return_value = make_mock_ticker()
    result = fetch_fundamentals("AAPL")
    assert result["pe_ratio"] == 28.4
    assert result["sector"] == "Technology"
    assert result["debt_equity"] == pytest.approx(1.7)
    assert isinstance(result["missing_fields"], list)


@patch("data.fetcher.yf.Ticker")
def test_fetch_fundamentals_marks_missing_fields(mock_ticker_cls):
    mock = make_mock_ticker(info={"sector": "Technology"})
    mock_ticker_cls.return_value = mock
    result = fetch_fundamentals("AAPL")
    assert "pe_ratio" in result["missing_fields"]
    assert result["pe_ratio"] is None


@patch("data.fetcher.yf.Ticker")
def test_fetch_ohlcv_empty_history_returns_empty_lists(mock_ticker_cls):
    mock = make_mock_ticker(history=pd.DataFrame())
    mock_ticker_cls.return_value = mock
    result = fetch_ohlcv("AAPL")
    assert result["dates"] == []
