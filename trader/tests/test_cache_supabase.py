"""Tests for Supabase-backed cache.py.

All Supabase calls are mocked — no real network calls.
"""
from unittest.mock import MagicMock, patch


def _mock_client(read_data=None):
    """Build a mock Supabase client that returns read_data on .execute()."""
    client = MagicMock()
    execute_result = MagicMock()
    execute_result.data = read_data or []
    # Chain: client.table().select().eq().execute()
    (client.table.return_value
           .select.return_value
           .eq.return_value
           .execute.return_value) = execute_result
    # Chain for upsert: client.table().upsert().execute()
    (client.table.return_value
           .upsert.return_value
           .execute.return_value) = MagicMock()
    # Chain for delete: client.table().delete().eq().execute()
    (client.table.return_value
           .delete.return_value
           .eq.return_value
           .execute.return_value) = MagicMock()
    # Chain for insert: client.table().insert().execute()
    (client.table.return_value
           .insert.return_value
           .execute.return_value) = MagicMock()
    return client


def test_read_cache_returns_data_when_found():
    with patch("cache._get_client") as mock_get:
        mock_get.return_value = _mock_client(read_data=[{"data": {"ohlcv": {}}}])
        from cache import read_cache
        result = read_cache("AAPL")
    assert result == {"ohlcv": {}}


def test_read_cache_returns_none_when_not_found():
    with patch("cache._get_client") as mock_get:
        mock_get.return_value = _mock_client(read_data=[])
        from cache import read_cache
        result = read_cache("AAPL")
    assert result is None


def test_write_cache_calls_upsert():
    with patch("cache._get_client") as mock_get:
        client = _mock_client()
        mock_get.return_value = client
        from cache import write_cache
        write_cache("AAPL", {"ohlcv": {}})
    client.table.assert_called_with("tickers")
    client.table.return_value.upsert.assert_called_once()
    call_arg = client.table.return_value.upsert.call_args[0][0]
    assert call_arg["ticker"] == "AAPL"
    assert call_arg["data"] == {"ohlcv": {}}
    assert "updated_at" in call_arg


def test_get_watchlist_tickers_returns_list():
    client = _mock_client()
    execute_result = MagicMock()
    execute_result.data = [{"ticker": "AAPL"}, {"ticker": "MSFT"}]
    client.table.return_value.select.return_value.execute.return_value = execute_result
    with patch("cache._get_client", return_value=client):
        from cache import get_watchlist_tickers
        result = get_watchlist_tickers()
    assert result == ["AAPL", "MSFT"]


def test_add_watchlist_ticker_calls_insert():
    with patch("cache._get_client") as mock_get:
        client = _mock_client()
        mock_get.return_value = client
        from cache import add_watchlist_ticker
        add_watchlist_ticker("TSLA")
    client.table.assert_called_with("watchlist")
    client.table.return_value.insert.assert_called_once_with({"ticker": "TSLA"})


def test_remove_watchlist_ticker_calls_delete():
    with patch("cache._get_client") as mock_get:
        client = _mock_client()
        mock_get.return_value = client
        from cache import remove_watchlist_ticker
        remove_watchlist_ticker("TSLA")
    client.table.return_value.delete.return_value.eq.assert_called_with("ticker", "TSLA")
