import pytest

@pytest.fixture
def tmp_cache_dir(tmp_path):
    return str(tmp_path)

@pytest.fixture
def sample_cache_entry():
    return {
        "ticker": "AAPL",
        "updated_at": "2026-04-25T14:30:00Z",
        "fetch_error": False,
        "fetch_error_at": None,
        "sentiment_stale": False,
        "ohlcv": {
            "dates": ["2026-04-24", "2026-04-25"],
            "open": [170.0, 171.0],
            "high": [172.0, 173.0],
            "low": [169.0, 170.0],
            "close": [171.5, 172.0],
            "volume": [50000000, 55000000],
        },
        "fundamentals": {
            "pe_ratio": 28.4,
            "ev_ebitda": 21.1,
            "revenue_growth_yoy": 0.08,
            "gross_margin": 0.44,
            "operating_margin": 0.30,
            "debt_equity": 1.7,
            "sector": "Technology",
            "missing_fields": [],
        },
        "sentiment_items": [
            {
                "source": "google_news",
                "headline": "Apple beats earnings",
                "published_at": "2026-04-25T10:00:00Z",
                "label": "positive",
                "score": 0.91,
            }
        ],
        "scores": {
            "technical": 72,
            "fundamental": 65,
            "sentiment": 58,
            "final": 67,
            "verdict": "BUY",
            "patterns_detected": [],
            "technical_drivers": [],
            "fundamental_drivers": [],
            "sentiment_drivers": [],
        },
    }
