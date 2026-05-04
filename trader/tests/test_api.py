from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


from unittest.mock import patch


def test_get_watchlist_returns_list():
    mock_cache = {
        "ohlcv": {"close": [150.0], "dates": ["2026-04-30"]},
        "fundamentals": {"company_name": "Apple Inc", "missing_fields": []},
        "sentiment_items": [],
        "fetched_at": "2026-04-30T00:00:00+00:00",
        "_override_scores": {"technical": 70, "fundamental": 65, "sentiment": 60},
    }
    with patch("cache.get_watchlist_tickers", return_value=["AAPL"]):
        with patch("cache.read_cache", return_value=mock_cache):
            response = client.get("/api/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["ticker"] == "AAPL"
    assert "final_score" in data[0]
    assert "verdict" in data[0]


def test_get_watchlist_ticker_not_cached():
    with patch("cache.get_watchlist_tickers", return_value=["AAPL"]):
        with patch("cache.read_cache", return_value=None):
            response = client.get("/api/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["final_score"] is None


def test_add_watchlist_ticker():
    with patch("cache.add_watchlist_ticker") as mock_add:
        with patch("api.routers.watchlist._fetch_ticker_background"):
            response = client.post("/api/watchlist", json={"ticker": "tsla"})
    assert response.status_code == 200
    assert response.json()["ticker"] == "TSLA"
    mock_add.assert_called_once_with("TSLA")


def test_remove_watchlist_ticker():
    with patch("cache.remove_watchlist_ticker") as mock_remove:
        response = client.delete("/api/watchlist/AAPL")
    assert response.status_code == 200
    mock_remove.assert_called_once_with("AAPL")
