import pytest
from unittest.mock import patch, MagicMock
from data.sentiment import fetch_google_news, fetch_stocktwits, _retry_get


def mock_response(json_data=None, text="", status_code=200):
    m = MagicMock()
    m.status_code = status_code
    m.text = text
    m.json.return_value = json_data or {}
    return m


@patch("data.sentiment.feedparser.parse")
def test_fetch_google_news_returns_list_of_headlines(mock_parse):
    mock_parse.return_value = MagicMock(entries=[
        MagicMock(title="Apple soars on earnings", published="Thu, 25 Apr 2026 10:00:00 GMT"),
    ])
    result = fetch_google_news("AAPL")
    assert len(result) == 1
    assert result[0]["source"] == "google_news"
    assert "headline" in result[0]
    assert "published_at" in result[0]


@patch("data.sentiment.requests.get")
def test_fetch_stocktwits_returns_list(mock_get):
    mock_get.return_value = mock_response(json_data={
        "messages": [
            {"body": "AAPL to the moon!", "created_at": "2026-04-25T10:00:00Z"}
        ]
    })
    result = fetch_stocktwits("AAPL")
    assert len(result) == 1
    assert result[0]["source"] == "stocktwits"


@patch("data.sentiment.requests.get")
def test_retry_get_retries_on_429(mock_get):
    mock_get.side_effect = [
        mock_response(status_code=429),
        mock_response(status_code=429),
        mock_response(status_code=200, json_data={"messages": []}),
    ]
    result = _retry_get("http://example.com", max_retries=3, base_delay=0)
    assert result.status_code == 200
    assert mock_get.call_count == 3


@patch("data.sentiment.requests.get")
def test_retry_get_returns_none_after_max_retries(mock_get):
    mock_get.return_value = mock_response(status_code=429)
    result = _retry_get("http://example.com", max_retries=3, base_delay=0)
    assert result is None
