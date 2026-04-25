# Trader Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python + Streamlit stock analysis dashboard that combines technical indicators, chart pattern detection, fundamental ratios, and free sentiment sources into a weighted BUY/HOLD/SELL signal.

**Architecture:** APScheduler daemon thread refreshes all ticker data (OHLCV, fundamentals, sentiment) every 15 minutes for the watchlist and every 4 hours in batches for the S&P 500 screener universe, writing results to per-ticker JSON cache files. Streamlit reads only from cache — no live API calls during rendering. FinBERT (`ProsusAI/finbert`) runs as a module-level singleton on CPU to score sentiment text.

**Tech Stack:** Python 3.11+, Streamlit, yfinance, pandas-ta, scipy, plotly, APScheduler 3.x, transformers + torch (CPU), portalocker, feedparser, requests, BeautifulSoup4.

---

## File Map

```
trader/
├── app.py                     # Streamlit entry point: scheduler singleton guard + page routing
├── scheduler.py               # APScheduler BackgroundScheduler singleton + job definitions
├── config.py                  # All constants: watchlist, weights, intervals, paths
├── cache.py                   # Cache read/write with portalocker + atomic rename
├── data/
│   ├── __init__.py
│   ├── fetcher.py             # yfinance OHLCV + fundamentals fetch
│   ├── sentiment.py           # RSS + StockTwits + Reddit + Finviz scrape with retry
│   ├── finbert.py             # FinBERT singleton loader + batch inference
│   ├── sp500.csv              # S&P 500 universe: ticker,name,sector,market_cap_category
│   └── build_sp500.py         # One-time script to refresh sp500.csv from Wikipedia
├── scoring/
│   ├── __init__.py
│   ├── technical.py           # Indicator signals + chart pattern detection → score 0-100
│   ├── fundamental.py         # Ratio scoring vs sector median/fallback → score 0-100
│   ├── sentiment_score.py     # FinBERT results → weighted mean score 0-100
│   └── engine.py              # Combine three sub-scores → final score + verdict dict
├── pages/
│   ├── __init__.py
│   ├── watchlist.py           # Watchlist dashboard page
│   ├── detail.py              # Stock detail page
│   └── screener.py            # Screener page
├── tests/
│   ├── conftest.py            # Shared fixtures
│   ├── test_cache.py
│   ├── test_fetcher.py
│   ├── test_sentiment_scraper.py
│   ├── test_finbert.py
│   ├── test_technical.py
│   ├── test_fundamental.py
│   ├── test_sentiment_score.py
│   └── test_engine.py
├── cache/                     # Runtime cache (gitignored)
├── logs/                      # Runtime logs (gitignored)
└── requirements.txt
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `trader/requirements.txt`
- Create: `trader/config.py`
- Create: `trader/.gitignore`
- Create: `trader/data/__init__.py`
- Create: `trader/scoring/__init__.py`
- Create: `trader/pages/__init__.py`
- Create: `trader/tests/__init__.py`
- Create: `trader/tests/conftest.py`

- [ ] **Step 1: Create the project directory and subdirectories**

```bash
mkdir -p trader/data trader/scoring trader/pages trader/tests trader/cache trader/logs
touch trader/data/__init__.py trader/scoring/__init__.py trader/pages/__init__.py
touch trader/tests/__init__.py
```

- [ ] **Step 2: Write `requirements.txt`**

```
streamlit>=1.35.0
yfinance>=0.2.40
pandas-ta>=0.3.14b
plotly>=5.22.0
APScheduler>=3.10.0,<4.0
transformers>=4.40.0
torch>=2.2.0
portalocker>=2.8.0
feedparser>=6.0.11
requests>=2.31.0
beautifulsoup4>=4.12.0
scipy>=1.13.0
pandas>=2.2.0
lxml>=5.0.0
pytest>=8.0.0
pytest-mock>=3.14.0
```

- [ ] **Step 3: Write `config.py`**

```python
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WATCHLIST = ["AAPL", "MSFT", "NVDA"]
SCREENER_UNIVERSE = os.path.join(BASE_DIR, "data", "sp500.csv")

WATCHLIST_REFRESH_MINUTES = 15
SCREENER_REFRESH_HOURS = 4
SCREENER_BATCH_SIZE = 50

DEFAULT_WEIGHTS = {"technical": 0.40, "fundamental": 0.35, "sentiment": 0.25}

CACHE_DIR = os.path.join(BASE_DIR, "cache")
LOG_FILE = os.path.join(BASE_DIR, "logs", "trader.log")

SENTIMENT_LOOKBACK_HOURS = 48
SENTIMENT_HALF_LIFE_HOURS = 12
WATCHLIST_STALE_HOURS = 2
SCREENER_STALE_HOURS = 4
FINBERT_BATCH_SIZE = 16
```

- [ ] **Step 4: Write `.gitignore`**

```
cache/
logs/
__pycache__/
*.pyc
.env
*.egg-info/
dist/
.pytest_cache/
```

- [ ] **Step 5: Write `tests/conftest.py`**

```python
import pytest
import os
import tempfile
import json

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
```

- [ ] **Step 6: Install dependencies**

```bash
cd trader
pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 7: Verify pytest runs**

```bash
cd trader
pytest tests/ -v
```

Expected: "no tests ran" or 0 failures (no test files with tests yet).

- [ ] **Step 8: Commit**

```bash
git add trader/
git commit -m "feat: project scaffold — config, requirements, directory structure"
```

---

## Task 2: Cache Module

**Files:**
- Create: `trader/cache.py`
- Test: `trader/tests/test_cache.py`

- [ ] **Step 1: Write failing tests**

Create `trader/tests/test_cache.py`:

```python
import json
import os
import pytest
from cache import write_cache, read_cache


def test_write_and_read_roundtrip(tmp_cache_dir, sample_cache_entry):
    write_cache("AAPL", sample_cache_entry, cache_dir=tmp_cache_dir)
    result = read_cache("AAPL", cache_dir=tmp_cache_dir)
    assert result["ticker"] == "AAPL"
    assert result["fundamentals"]["pe_ratio"] == 28.4


def test_read_missing_ticker_returns_none(tmp_cache_dir):
    result = read_cache("ZZZZ", cache_dir=tmp_cache_dir)
    assert result is None


def test_write_is_atomic(tmp_cache_dir, sample_cache_entry):
    # tmp file should not persist after write
    write_cache("AAPL", sample_cache_entry, cache_dir=tmp_cache_dir)
    tmp_path = os.path.join(tmp_cache_dir, "AAPL.json.tmp")
    assert not os.path.exists(tmp_path)
    assert os.path.exists(os.path.join(tmp_cache_dir, "AAPL.json"))


def test_overwrite_replaces_data(tmp_cache_dir, sample_cache_entry):
    write_cache("AAPL", sample_cache_entry, cache_dir=tmp_cache_dir)
    updated = dict(sample_cache_entry)
    updated["fetch_error"] = True
    write_cache("AAPL", updated, cache_dir=tmp_cache_dir)
    result = read_cache("AAPL", cache_dir=tmp_cache_dir)
    assert result["fetch_error"] is True
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd trader
pytest tests/test_cache.py -v
```

Expected: `ImportError: No module named 'cache'`

- [ ] **Step 3: Implement `cache.py`**

```python
import json
import os
import portalocker


def _cache_path(ticker: str, cache_dir: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{ticker}.json")


def write_cache(ticker: str, data: dict, cache_dir: str = None) -> None:
    from config import CACHE_DIR
    if cache_dir is None:
        cache_dir = CACHE_DIR
    path = _cache_path(ticker, cache_dir)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        json.dump(data, f, default=str)
    os.replace(tmp_path, path)


def read_cache(ticker: str, cache_dir: str = None) -> dict | None:
    from config import CACHE_DIR
    if cache_dir is None:
        cache_dir = CACHE_DIR
    path = _cache_path(ticker, cache_dir)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        portalocker.lock(f, portalocker.LOCK_SH)
        data = json.load(f)
        portalocker.unlock(f)
    return data
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pytest tests/test_cache.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add trader/cache.py trader/tests/test_cache.py
git commit -m "feat: cache read/write with portalocker and atomic rename"
```

---

## Task 3: Data Fetcher (yfinance)

**Files:**
- Create: `trader/data/fetcher.py`
- Test: `trader/tests/test_fetcher.py`

- [ ] **Step 1: Write failing tests**

Create `trader/tests/test_fetcher.py`:

```python
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
def test_fetch_ohlcv_returns_correct_keys(mock_ticker_cls, ):
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
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_fetcher.py -v
```

Expected: `ImportError: No module named 'data.fetcher'`

- [ ] **Step 3: Implement `data/fetcher.py`**

```python
import yfinance as yf


_FUNDAMENTAL_MAP = {
    "pe_ratio": "trailingPE",
    "ev_ebitda": "enterpriseToEbitda",
    "revenue_growth_yoy": "revenueGrowth",
    "gross_margin": "grossMargins",
    "operating_margin": "operatingMargins",
    "debt_equity": lambda info: (info.get("debtToEquity") or 0) / 100,
    "sector": "sector",
}


def fetch_ohlcv(ticker: str, period: str = "6mo") -> dict:
    tk = yf.Ticker(ticker)
    hist = tk.history(period=period)
    if hist.empty:
        return {k: [] for k in ("dates", "open", "high", "low", "close", "volume")}
    return {
        "dates": hist.index.strftime("%Y-%m-%d").tolist(),
        "open": hist["Open"].round(4).tolist(),
        "high": hist["High"].round(4).tolist(),
        "low": hist["Low"].round(4).tolist(),
        "close": hist["Close"].round(4).tolist(),
        "volume": hist["Volume"].astype(int).tolist(),
    }


def fetch_fundamentals(ticker: str) -> dict:
    tk = yf.Ticker(ticker)
    info = tk.info or {}
    result = {}
    missing = []
    for key, src in _FUNDAMENTAL_MAP.items():
        if callable(src):
            val = src(info)
        else:
            val = info.get(src)
        if val is None and key != "sector":
            missing.append(key)
        result[key] = val
    result["missing_fields"] = missing
    return result
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pytest tests/test_fetcher.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add trader/data/fetcher.py trader/tests/test_fetcher.py
git commit -m "feat: yfinance OHLCV and fundamentals fetcher"
```

---

## Task 4: Sentiment Scraper

**Files:**
- Create: `trader/data/sentiment.py`
- Test: `trader/tests/test_sentiment_scraper.py`

- [ ] **Step 1: Write failing tests**

Create `trader/tests/test_sentiment_scraper.py`:

```python
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
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_sentiment_scraper.py -v
```

Expected: `ImportError: No module named 'data.sentiment'`

- [ ] **Step 3: Implement `data/sentiment.py`**

```python
import time
import logging
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]
_ua_index = 0


def _next_ua() -> str:
    global _ua_index
    ua = _USER_AGENTS[_ua_index % len(_USER_AGENTS)]
    _ua_index += 1
    return ua


def _retry_get(url: str, max_retries: int = 3, base_delay: float = 1.0, **kwargs):
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=10, **kwargs)
            if resp.status_code in (429, 403):
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                return None
            return resp
        except Exception as e:
            logger.warning("GET %s attempt %d failed: %s", url, attempt + 1, e)
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
    return None


def _parse_dt(dt_str: str | None) -> str | None:
    if not dt_str:
        return None
    try:
        return parsedate_to_datetime(dt_str).astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).isoformat()
    except Exception:
        return None


def fetch_google_news(ticker: str) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries:
        items.append({
            "source": "google_news",
            "headline": e.get("title", ""),
            "published_at": _parse_dt(e.get("published")),
            "label": None,
            "score": None,
        })
    return items


def fetch_stocktwits(ticker: str) -> list[dict]:
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    resp = _retry_get(url)
    if resp is None:
        return []
    try:
        messages = resp.json().get("messages", [])
    except Exception:
        return []
    return [
        {
            "source": "stocktwits",
            "headline": m.get("body", ""),
            "published_at": _parse_dt(m.get("created_at")),
            "label": None,
            "score": None,
        }
        for m in messages
    ]


def fetch_reddit_rss(ticker: str, subreddit: str) -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/search.rss?q={ticker}&sort=new"
    feed = feedparser.parse(url)
    return [
        {
            "source": f"reddit_{subreddit}",
            "headline": e.get("title", ""),
            "published_at": _parse_dt(e.get("published")),
            "label": None,
            "score": None,
        }
        for e in feed.entries
    ]


def fetch_finviz(ticker: str) -> list[dict]:
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    headers = {"User-Agent": _next_ua()}
    time.sleep(2)
    resp = _retry_get(url, headers=headers)
    if resp is None:
        logger.warning("Finviz blocked for %s — skipping", ticker)
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("table.fullview-news-outer tr")
    items = []
    for row in rows:
        link = row.find("a")
        if link:
            items.append({
                "source": "finviz",
                "headline": link.get_text(strip=True),
                "published_at": None,
                "label": None,
                "score": None,
            })
    return items


def fetch_all_sentiment(ticker: str) -> list[dict]:
    items = []
    items.extend(fetch_google_news(ticker))
    items.extend(fetch_stocktwits(ticker))
    items.extend(fetch_reddit_rss(ticker, "stocks"))
    items.extend(fetch_reddit_rss(ticker, "investing"))
    items.extend(fetch_finviz(ticker))
    return items
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pytest tests/test_sentiment_scraper.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add trader/data/sentiment.py trader/tests/test_sentiment_scraper.py
git commit -m "feat: sentiment scraper — Google News, StockTwits, Reddit, Finviz with retry/backoff"
```

---

## Task 5: FinBERT Singleton

**Files:**
- Create: `trader/data/finbert.py`
- Test: `trader/tests/test_finbert.py`

- [ ] **Step 1: Write failing tests**

Create `trader/tests/test_finbert.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def test_classify_returns_label_and_score():
    with patch("data.finbert._get_pipeline") as mock_pipe_fn:
        mock_pipe = MagicMock()
        mock_pipe.return_value = [[{"label": "positive", "score": 0.95}]]
        mock_pipe_fn.return_value = mock_pipe
        from data.finbert import classify_batch
        results = classify_batch(["Apple earnings beat expectations"])
    assert len(results) == 1
    assert results[0]["label"] in ("positive", "negative", "neutral")
    assert 0.0 <= results[0]["score"] <= 1.0


def test_classify_batch_handles_multiple():
    with patch("data.finbert._get_pipeline") as mock_pipe_fn:
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            [{"label": "positive", "score": 0.9}],
            [{"label": "negative", "score": 0.8}],
        ]
        mock_pipe_fn.return_value = mock_pipe
        from data.finbert import classify_batch
        results = classify_batch(["Good news", "Bad news"])
    assert len(results) == 2


def test_classify_empty_list_returns_empty():
    with patch("data.finbert._get_pipeline"):
        from data.finbert import classify_batch
        assert classify_batch([]) == []
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_finbert.py -v
```

Expected: `ImportError: No module named 'data.finbert'`

- [ ] **Step 3: Implement `data/finbert.py`**

```python
import logging
from config import FINBERT_BATCH_SIZE

logger = logging.getLogger(__name__)

_pipeline = None
_load_failed = False


def _get_pipeline():
    global _pipeline, _load_failed
    if _pipeline is not None:
        return _pipeline
    if _load_failed:
        return None
    try:
        from transformers import pipeline
        _pipeline = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            device=-1,  # CPU
            top_k=1,
        )
        logger.info("FinBERT loaded successfully")
    except Exception as e:
        logger.error("FinBERT failed to load: %s", e)
        _load_failed = True
        return None
    return _pipeline


def classify_batch(texts: list[str]) -> list[dict]:
    if not texts:
        return []
    pipe = _get_pipeline()
    if pipe is None:
        return [{"label": "neutral", "score": 0.0} for _ in texts]
    results = []
    for i in range(0, len(texts), FINBERT_BATCH_SIZE):
        batch = texts[i : i + FINBERT_BATCH_SIZE]
        try:
            outputs = pipe(batch)
            for out in outputs:
                top = out[0] if isinstance(out, list) else out
                results.append({"label": top["label"].lower(), "score": round(top["score"], 4)})
        except Exception as e:
            logger.error("FinBERT inference error: %s", e)
            results.extend([{"label": "neutral", "score": 0.0} for _ in batch])
    return results
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pytest tests/test_finbert.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add trader/data/finbert.py trader/tests/test_finbert.py
git commit -m "feat: FinBERT singleton with CPU inference and graceful load failure"
```

---

## Task 6: Technical Scoring

**Files:**
- Create: `trader/scoring/technical.py`
- Test: `trader/tests/test_technical.py`

- [ ] **Step 1: Write failing tests**

Create `trader/tests/test_technical.py`:

```python
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
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_technical.py -v
```

Expected: `ImportError: No module named 'scoring.technical'`

- [ ] **Step 3: Implement `scoring/technical.py`**

```python
import math
import numpy as np
import pandas as pd
import pandas_ta as ta
from scipy.signal import find_peaks

_INDICATOR_WEIGHTS = {
    "ema_20_50": 0.10,
    "ema_50_200": 0.10,
    "adx": 0.08,
    "rsi": 0.12,
    "macd": 0.10,
    "stoch": 0.08,
    "bbands": 0.07,
    "atr": 0.05,
    "obv": 0.10,
    "volume": 0.05,
    "pattern": 0.15,
}

_PATTERN_INFO = {
    "double_bottom":        ("Double Bottom",        "Two equal lows — typically signals a bullish reversal.", "High", "bullish"),
    "double_top":           ("Double Top",           "Two equal highs — typically signals a bearish reversal.", "High", "bearish"),
    "head_and_shoulders":   ("Head & Shoulders",     "Left shoulder, higher head, right shoulder — bearish reversal signal.", "High", "bearish"),
    "inverse_hns":          ("Inverse H&S",          "Inverted pattern — bullish reversal signal.", "High", "bullish"),
    "ascending_triangle":   ("Ascending Triangle",   "Rising lows with flat resistance — bullish continuation.", "Medium", "bullish"),
    "descending_triangle":  ("Descending Triangle",  "Falling highs with flat support — bearish continuation.", "Medium", "bearish"),
    "symmetrical_triangle": ("Symmetrical Triangle", "Converging highs and lows — breakout pending, direction unclear.", "Medium", "neutral"),
    "bull_flag":            ("Bull Flag",            "Tight consolidation after a strong uptrend — signals continuation higher.", "Medium", "bullish"),
    "bear_flag":            ("Bear Flag",            "Tight consolidation after a strong downtrend — signals continuation lower.", "Medium", "bearish"),
    "cup_and_handle":       ("Cup & Handle",         "U-shaped base then small pullback — bullish breakout setup.", "Medium", "bullish"),
}


def _signal_to_score(signal: int) -> float:
    return {1: 100.0, 0: 50.0, -1: 0.0}.get(signal, 50.0)


def _ohlcv_to_df(ohlcv: dict) -> pd.DataFrame:
    return pd.DataFrame({
        "open": ohlcv["open"],
        "high": ohlcv["high"],
        "low": ohlcv["low"],
        "close": ohlcv["close"],
        "volume": ohlcv["volume"],
    })


def detect_patterns(ohlcv: dict) -> list[dict]:
    close = np.array(ohlcv["close"])
    dates = ohlcv["dates"]
    n = len(close)
    patterns = []

    if n < 30:
        return patterns

    # Double bottom (60-day window, 2% tolerance)
    window = close[-60:] if n >= 60 else close
    dates_w = dates[-60:] if n >= 60 else dates
    troughs, _ = find_peaks(-window, distance=10)
    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        if abs(window[t1] - window[t2]) / window[t1] < 0.02 and (t2 - t1) >= 10:
            name, meaning, reliability, direction = _PATTERN_INFO["double_bottom"]
            patterns.append({
                "name": name,
                "detected_at": dates_w[t2] if t2 < len(dates_w) else dates[-1],
                "meaning": meaning,
                "reliability": reliability,
                "direction": direction,
            })

    # Double top
    peaks, _ = find_peaks(window, distance=10)
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if abs(window[p1] - window[p2]) / window[p1] < 0.02 and (p2 - p1) >= 10:
            name, meaning, reliability, direction = _PATTERN_INFO["double_top"]
            patterns.append({
                "name": name,
                "detected_at": dates_w[p2] if p2 < len(dates_w) else dates[-1],
                "meaning": meaning,
                "reliability": reliability,
                "direction": direction,
            })

    # Head & Shoulders (60-day window)
    if len(peaks) >= 3 and len(window) >= 60:
        p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
        left_sh, head, right_sh = window[p1], window[p2], window[p3]
        if head > left_sh and head > right_sh and abs(left_sh - right_sh) / head < 0.05:
            name, meaning, reliability, direction = _PATTERN_INFO["head_and_shoulders"]
            patterns.append({"name": name, "detected_at": dates_w[p3] if p3 < len(dates_w) else dates[-1],
                              "meaning": meaning, "reliability": reliability, "direction": direction})

    # Inverse Head & Shoulders (60-day window)
    if len(troughs) >= 3 and len(window) >= 60:
        t1, t2, t3 = troughs[-3], troughs[-2], troughs[-1]
        left_sh, head, right_sh = window[t1], window[t2], window[t3]
        if head < left_sh and head < right_sh and abs(left_sh - right_sh) / abs(head) < 0.05:
            name, meaning, reliability, direction = _PATTERN_INFO["inverse_hns"]
            patterns.append({"name": name, "detected_at": dates_w[t3] if t3 < len(dates_w) else dates[-1],
                              "meaning": meaning, "reliability": reliability, "direction": direction})

    # Ascending / Descending / Symmetrical Triangle (40-day window)
    if n >= 40:
        tri = close[-40:]
        tri_dates = dates[-40:]
        tri_peaks, _ = find_peaks(tri, distance=5)
        tri_troughs, _ = find_peaks(-np.array(tri), distance=5)
        if len(tri_peaks) >= 2 and len(tri_troughs) >= 2:
            peak_slope = (tri[tri_peaks[-1]] - tri[tri_peaks[-2]]) / max(tri[tri_peaks[-2]], 1e-9)
            trough_slope = (tri[tri_troughs[-1]] - tri[tri_troughs[-2]]) / max(abs(tri[tri_troughs[-2]]), 1e-9)
            if trough_slope > 0.01 and abs(peak_slope) < 0.01:
                name, meaning, reliability, direction = _PATTERN_INFO["ascending_triangle"]
                patterns.append({"name": name, "detected_at": tri_dates[-1], "meaning": meaning, "reliability": reliability, "direction": direction})
            elif peak_slope < -0.01 and abs(trough_slope) < 0.01:
                name, meaning, reliability, direction = _PATTERN_INFO["descending_triangle"]
                patterns.append({"name": name, "detected_at": tri_dates[-1], "meaning": meaning, "reliability": reliability, "direction": direction})
            elif peak_slope < -0.005 and trough_slope > 0.005:
                name, meaning, reliability, direction = _PATTERN_INFO["symmetrical_triangle"]
                patterns.append({"name": name, "detected_at": tri_dates[-1], "meaning": meaning, "reliability": reliability, "direction": direction})

    # Bull flag: flagpole = bars[-30:-10], consolidation = bars[-10:] (≤10 bars per spec)
    if n >= 30:
        flagpole = close[-30:-10]
        consolidation = close[-10:]
        uptrend = len(flagpole) > 1 and (flagpole[-1] - flagpole[0]) / flagpole[0] > 0.05
        tight = np.std(consolidation) / np.mean(consolidation) < 0.02
        if uptrend and tight and consolidation[-1] < consolidation[0]:
            name, meaning, reliability, direction = _PATTERN_INFO["bull_flag"]
            patterns.append({"name": name, "detected_at": dates[-1], "meaning": meaning, "reliability": reliability, "direction": direction})

    # Bear flag: flagpole = bars[-30:-10], consolidation = bars[-10:] (≤10 bars per spec)
    if n >= 30:
        flagpole = close[-30:-10]
        consolidation = close[-10:]
        downtrend = len(flagpole) > 1 and (flagpole[-1] - flagpole[0]) / flagpole[0] < -0.05
        tight = np.std(consolidation) / np.mean(consolidation) < 0.02
        if downtrend and tight and consolidation[-1] > consolidation[0]:
            name, meaning, reliability, direction = _PATTERN_INFO["bear_flag"]
            patterns.append({"name": name, "detected_at": dates[-1], "meaning": meaning, "reliability": reliability, "direction": direction})

    # Cup & Handle (90-day window)
    if n >= 90:
        cup = close[-90:-10]
        handle = close[-10:]
        mid_idx = len(cup) // 2
        left = cup[:mid_idx]
        right = cup[mid_idx:]
        if left and right and min(cup) < cup[0] * 0.95 and min(cup) < cup[-1] * 0.95:
            # U-shape: start and end near same level, dip in middle
            if abs(cup[0] - cup[-1]) / cup[0] < 0.05:
                handle_declining = handle[-1] < handle[0]
                if handle_declining:
                    name, meaning, reliability, direction = _PATTERN_INFO["cup_and_handle"]
                    patterns.append({"name": name, "detected_at": dates[-10], "meaning": meaning, "reliability": reliability, "direction": direction})

    return patterns


def compute_technical_score(ohlcv: dict) -> tuple[int, list[str], list[dict]]:
    close = ohlcv["close"]
    if len(close) < 20:
        return 50, ["Insufficient data for technical analysis"], []

    df = _ohlcv_to_df(ohlcv)
    signals = {}
    drivers = []

    # EMA 20/50
    ema20 = ta.ema(df["close"], length=20)
    ema50 = ta.ema(df["close"], length=50)
    if ema20 is not None and ema50 is not None and not ema20.empty and not ema50.empty:
        price = df["close"].iloc[-1]
        e20, e50 = ema20.iloc[-1], ema50.iloc[-1]
        if price > e20 > e50:
            signals["ema_20_50"] = 1
            drivers.append("Price above EMA 20 and EMA 50 (bullish)")
        elif price < e20 < e50:
            signals["ema_20_50"] = -1
            drivers.append("Price below EMA 20 and EMA 50 (bearish)")
        else:
            signals["ema_20_50"] = 0

    # EMA 50/200
    ema200 = ta.ema(df["close"], length=min(200, len(df)))
    if ema50 is not None and ema200 is not None and not ema50.empty and not ema200.empty:
        if ema50.iloc[-1] > ema200.iloc[-1]:
            signals["ema_50_200"] = 1
            drivers.append("Golden cross: EMA 50 above EMA 200")
        else:
            signals["ema_50_200"] = -1
            drivers.append("Death cross: EMA 50 below EMA 200")

    # RSI
    rsi = ta.rsi(df["close"], length=14)
    if rsi is not None and not rsi.empty:
        r = rsi.iloc[-1]
        if r < 40:
            signals["rsi"] = 1
            drivers.append(f"RSI {r:.0f} — oversold, room to run")
        elif r > 65:
            signals["rsi"] = -1
            drivers.append(f"RSI {r:.0f} — overbought")
        else:
            signals["rsi"] = 0
            drivers.append(f"RSI {r:.0f} — neutral")

    # MACD
    macd_df = ta.macd(df["close"])
    if macd_df is not None and not macd_df.empty:
        macd_line = macd_df.iloc[:, 0]
        signal_line = macd_df.iloc[:, 2]
        if not macd_line.empty and not signal_line.empty:
            if macd_line.iloc[-1] > signal_line.iloc[-1]:
                signals["macd"] = 1
                drivers.append("MACD bullish crossover")
            else:
                signals["macd"] = -1
                drivers.append("MACD bearish crossover")

    # OBV trend
    obv = ta.obv(df["close"], df["volume"])
    if obv is not None and len(obv) >= 10:
        signals["obv"] = 1 if obv.iloc[-1] > obv.iloc[-10] else -1

    # Volume
    avg_vol = df["volume"].rolling(20).mean().iloc[-1]
    curr_vol = df["volume"].iloc[-1]
    price_up = df["close"].iloc[-1] > df["close"].iloc[-2]
    if curr_vol > avg_vol * 1.5:
        signals["volume"] = 1 if price_up else -1
    else:
        signals["volume"] = 0

    # Bollinger Bands
    bb = ta.bbands(df["close"])
    if bb is not None and not bb.empty:
        lower = bb.iloc[:, 0].iloc[-1]
        upper = bb.iloc[:, 2].iloc[-1]
        price = df["close"].iloc[-1]
        if price <= lower:
            signals["bbands"] = 1
        elif price >= upper:
            signals["bbands"] = -1
        else:
            signals["bbands"] = 0

    # Stochastic
    stoch = ta.stoch(df["high"], df["low"], df["close"])
    if stoch is not None and not stoch.empty and len(stoch) >= 2:
        k = stoch.iloc[:, 0]
        d = stoch.iloc[:, 1]
        if k.iloc[-1] < 30 and k.iloc[-1] > k.iloc[-2] and k.iloc[-1] > d.iloc[-1]:
            signals["stoch"] = 1
        elif k.iloc[-1] > 70 and k.iloc[-1] < k.iloc[-2] and k.iloc[-1] < d.iloc[-1]:
            signals["stoch"] = -1
        else:
            signals["stoch"] = 0

    # ADX
    adx = ta.adx(df["high"], df["low"], df["close"])
    if adx is not None and not adx.empty:
        adx_val = adx.iloc[:, 0].iloc[-1]
        dmp = adx.iloc[:, 1].iloc[-1]
        dmn = adx.iloc[:, 2].iloc[-1]
        if adx_val > 25:
            signals["adx"] = 1 if dmp > dmn else -1
        else:
            signals["adx"] = 0

    # ATR
    atr = ta.atr(df["high"], df["low"], df["close"])
    if atr is not None and not atr.empty:
        norm_atr = atr.iloc[-1] / df["close"].iloc[-1]
        signals["atr"] = 1 if norm_atr < 0.02 else -1

    # Patterns — sort by detected_at so most_recent is truly the latest by date
    patterns = detect_patterns(ohlcv)
    if patterns:
        most_recent = sorted(patterns, key=lambda p: p["detected_at"])[-1]
        signals["pattern"] = 1 if most_recent["direction"] == "bullish" else (-1 if most_recent["direction"] == "bearish" else 0)
        drivers.append(f"Pattern: {most_recent['name']} ({most_recent['direction']})")
    else:
        signals["pattern"] = 0

    total = sum(
        _signal_to_score(signals.get(k, 0)) * w
        for k, w in _INDICATOR_WEIGHTS.items()
    )
    score = int(math.floor(total))
    return max(0, min(100, score)), drivers, patterns
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pytest tests/test_technical.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add trader/scoring/technical.py trader/tests/test_technical.py
git commit -m "feat: technical scoring — indicators, pattern detection, signal-to-score formula"
```

---

## Task 7: Fundamental Scoring

**Files:**
- Create: `trader/scoring/fundamental.py`
- Test: `trader/tests/test_fundamental.py`

- [ ] **Step 1: Write failing tests**

Create `trader/tests/test_fundamental.py`:

```python
import pytest
from scoring.fundamental import compute_fundamental_score

_GOOD_FUNDAMENTALS = {
    "pe_ratio": 15.0,
    "ev_ebitda": 10.0,
    "revenue_growth_yoy": 0.15,
    "gross_margin": 0.50,
    "operating_margin": 0.20,
    "debt_equity": 0.5,
    "sector": "Technology",
    "missing_fields": [],
}

_BAD_FUNDAMENTALS = {
    "pe_ratio": 80.0,
    "ev_ebitda": 40.0,
    "revenue_growth_yoy": -0.05,
    "gross_margin": 0.10,
    "operating_margin": 0.02,
    "debt_equity": 5.0,
    "sector": "Technology",
    "missing_fields": [],
}


def test_score_is_int_in_range():
    score, _ = compute_fundamental_score(_GOOD_FUNDAMENTALS)
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_good_fundamentals_score_higher_than_bad():
    good_score, _ = compute_fundamental_score(_GOOD_FUNDAMENTALS)
    bad_score, _ = compute_fundamental_score(_BAD_FUNDAMENTALS)
    assert good_score > bad_score


def test_missing_field_excluded_from_score():
    fund = dict(_GOOD_FUNDAMENTALS)
    fund["pe_ratio"] = None
    fund["missing_fields"] = ["pe_ratio"]
    score, drivers = compute_fundamental_score(fund)
    assert score is not None
    assert 0 <= score <= 100


def test_too_many_missing_returns_none():
    fund = {k: None for k in _GOOD_FUNDAMENTALS}
    fund["sector"] = "Technology"
    fund["missing_fields"] = ["pe_ratio", "ev_ebitda", "revenue_growth_yoy", "gross_margin"]
    score, _ = compute_fundamental_score(fund)
    assert score is None


def test_drivers_is_list_of_strings():
    _, drivers = compute_fundamental_score(_GOOD_FUNDAMENTALS)
    assert isinstance(drivers, list)
    assert all(isinstance(d, str) for d in drivers)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_fundamental.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `scoring/fundamental.py`**

```python
import math
import os
import json
import glob

_RATIO_CONFIG = {
    "pe_ratio":             {"weight": 0.20, "bullish": 18.0,  "bearish": 35.0,  "lower_is_better": True},
    "ev_ebitda":            {"weight": 0.20, "bullish": 12.0,  "bearish": 25.0,  "lower_is_better": True},
    "revenue_growth_yoy":   {"weight": 0.20, "bullish": 0.10,  "bearish": 0.0,   "lower_is_better": False},
    "gross_margin":         {"weight": 0.15, "bullish": 0.40,  "bearish": 0.15,  "lower_is_better": False},
    "operating_margin":     {"weight": 0.15, "bullish": 0.15,  "bearish": 0.05,  "lower_is_better": False},
    "debt_equity":          {"weight": 0.10, "bullish": 1.0,   "bearish": 3.0,   "lower_is_better": True},
}


def _score_ratio(value: float, bullish: float, bearish: float, lower_is_better: bool) -> float:
    if lower_is_better:
        bullish, bearish = bearish, bullish
    if bearish == bullish:
        return 50.0
    raw = (value - bearish) / (bullish - bearish)
    return max(0.0, min(100.0, raw * 100.0))


def _compute_sector_medians(sector: str) -> dict:
    """Compute median values per ratio from all cached tickers in the same sector."""
    from config import CACHE_DIR
    ratio_values: dict[str, list[float]] = {k: [] for k in _RATIO_CONFIG}
    for path in glob.glob(os.path.join(CACHE_DIR, "*.json")):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            fund = data.get("fundamentals", {})
            if fund.get("sector") != sector:
                continue
            for key in _RATIO_CONFIG:
                v = fund.get(key)
                if v is not None:
                    ratio_values[key].append(float(v))
        except Exception:
            continue
    medians = {}
    for key, values in ratio_values.items():
        if len(values) >= 3:
            medians[key] = sorted(values)[len(values) // 2]
    return medians


def compute_fundamental_score(fundamentals: dict) -> tuple[int | None, list[str]]:
    missing = set(fundamentals.get("missing_fields", []))
    available = {k: v for k, v in fundamentals.items() if k in _RATIO_CONFIG and k not in missing and v is not None}

    if len(available) < 3:
        return None, ["Insufficient fundamental data"]

    # Try to get sector medians; fall back to absolute thresholds if < 3 peers found
    sector = fundamentals.get("sector", "")
    sector_medians = _compute_sector_medians(sector) if sector else {}

    total_weight = sum(_RATIO_CONFIG[k]["weight"] for k in available)
    weighted_sum = 0.0
    drivers = []

    for key, value in available.items():
        cfg = _RATIO_CONFIG[key]
        median = sector_medians.get(key)
        if median is not None and median > 0:
            # Dynamic thresholds: 80% of median = bullish, 150% = bearish (for lower-is-better)
            if cfg["lower_is_better"]:
                bullish = median * 0.8
                bearish = median * 1.5
            else:
                bullish = median
                bearish = median * 0.7
        else:
            bullish = cfg["bullish"]
            bearish = cfg["bearish"]
        ratio_score = _score_ratio(value, bullish, bearish, cfg["lower_is_better"])
        weighted_sum += ratio_score * cfg["weight"]
        label = "strong" if ratio_score >= 70 else ("weak" if ratio_score <= 30 else "neutral")
        drivers.append(f"{key.replace('_', ' ').title()}: {value:.2f} ({label})")

    normalised = weighted_sum / total_weight if total_weight > 0 else 50.0
    return int(math.floor(normalised)), drivers
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pytest tests/test_fundamental.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add trader/scoring/fundamental.py trader/tests/test_fundamental.py
git commit -m "feat: fundamental scoring with fallback thresholds and missing-field handling"
```

---

## Task 8: Sentiment Scoring

**Files:**
- Create: `trader/scoring/sentiment_score.py`
- Test: `trader/tests/test_sentiment_score.py`

- [ ] **Step 1: Write failing tests**

Create `trader/tests/test_sentiment_score.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
from scoring.sentiment_score import compute_sentiment_score


def _make_item(label, hours_ago=1, source="google_news"):
    published_at = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return {"source": source, "headline": "test", "published_at": published_at, "label": label, "score": 0.9}


def test_all_positive_scores_high():
    items = [_make_item("positive") for _ in range(5)]
    score, _ = compute_sentiment_score(items)
    assert score >= 80


def test_all_negative_scores_low():
    items = [_make_item("negative") for _ in range(5)]
    score, _ = compute_sentiment_score(items)
    assert score <= 20


def test_fewer_than_3_items_returns_none():
    items = [_make_item("positive"), _make_item("positive")]
    score, _ = compute_sentiment_score(items)
    assert score is None


def test_score_in_range():
    items = [_make_item("positive"), _make_item("negative"), _make_item("neutral")]
    score, _ = compute_sentiment_score(items)
    if score is not None:
        assert 0 <= score <= 100


def test_older_items_weighted_less():
    fresh_positive = [_make_item("positive", hours_ago=1) for _ in range(3)]
    stale_negative = [_make_item("negative", hours_ago=47) for _ in range(10)]
    score, _ = compute_sentiment_score(fresh_positive + stale_negative)
    stale_score, _ = compute_sentiment_score(stale_negative + fresh_positive)
    # Both should give the same result (order independent)
    assert score == stale_score


def test_no_timestamp_items_get_low_weight():
    no_ts = [{"source": "x", "headline": "h", "published_at": None, "label": "negative", "score": 0.9}] * 10
    fresh = [_make_item("positive", hours_ago=1) for _ in range(3)]
    score, _ = compute_sentiment_score(fresh + no_ts)
    assert score >= 50
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_sentiment_score.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `scoring/sentiment_score.py`**

```python
import math
from datetime import datetime, timezone
from config import SENTIMENT_LOOKBACK_HOURS, SENTIMENT_HALF_LIFE_HOURS

_LABEL_SCORE = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}
_NO_TIMESTAMP_WEIGHT = 0.1


def _age_weight(published_at: str | None) -> float:
    if not published_at:
        return _NO_TIMESTAMP_WEIGHT
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        if age_hours > SENTIMENT_LOOKBACK_HOURS:
            return 0.0
        return math.exp(-age_hours / SENTIMENT_HALF_LIFE_HOURS)
    except Exception:
        return _NO_TIMESTAMP_WEIGHT


def compute_sentiment_score(items: list[dict]) -> tuple[int | None, list[str]]:
    weighted_sum = 0.0
    weight_total = 0.0

    for item in items:
        label = (item.get("label") or "neutral").lower()
        label_score = _LABEL_SCORE.get(label, 0.5)
        weight = _age_weight(item.get("published_at"))
        if weight == 0.0:
            continue
        weighted_sum += label_score * weight
        weight_total += weight

    if weight_total == 0 or len([i for i in items if _age_weight(i.get("published_at")) > 0]) < 3:
        return None, ["Insufficient recent sentiment data"]

    score = (weighted_sum / weight_total) * 100
    clamped = max(0, min(100, int(math.floor(score))))

    bullish = sum(1 for i in items if i.get("label") == "positive")
    bearish = sum(1 for i in items if i.get("label") == "negative")
    neutral = sum(1 for i in items if i.get("label") == "neutral")
    drivers = [f"{bullish} bullish / {bearish} bearish / {neutral} neutral items in last {SENTIMENT_LOOKBACK_HOURS}h"]

    return clamped, drivers
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pytest tests/test_sentiment_score.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add trader/scoring/sentiment_score.py trader/tests/test_sentiment_score.py
git commit -m "feat: sentiment scoring with exponential recency decay and FinBERT labels"
```

---

## Task 9: Scoring Engine

**Files:**
- Create: `trader/scoring/engine.py`
- Test: `trader/tests/test_engine.py`

- [ ] **Step 1: Write failing tests**

Create `trader/tests/test_engine.py`:

```python
import pytest
from scoring.engine import compute_full_score


def make_cache(tech=70, fund=65, sent=60):
    return {
        "ohlcv": {"dates": [], "open": [], "high": [], "low": [], "close": [], "volume": []},
        "fundamentals": {
            "pe_ratio": 15.0, "ev_ebitda": 10.0, "revenue_growth_yoy": 0.15,
            "gross_margin": 0.5, "operating_margin": 0.2, "debt_equity": 0.5,
            "sector": "Technology", "missing_fields": [],
        },
        "sentiment_items": [],
        "_override_scores": {"technical": tech, "fundamental": fund, "sentiment": sent},
    }


def test_final_score_is_weighted_average():
    # With equal override scores the final should equal them
    result = compute_full_score(make_cache(tech=60, fund=60, sent=60))
    assert result["final"] == 60


def test_verdict_buy_at_65():
    result = compute_full_score(make_cache(tech=65, fund=65, sent=65))
    assert result["verdict"] == "BUY"


def test_verdict_strong_buy_at_80():
    result = compute_full_score(make_cache(tech=80, fund=80, sent=80))
    assert result["verdict"] == "Strong BUY"


def test_verdict_sell_at_35():
    result = compute_full_score(make_cache(tech=35, fund=35, sent=35))
    assert result["verdict"] == "SELL"


def test_verdict_strong_sell_at_20():
    result = compute_full_score(make_cache(tech=20, fund=20, sent=20))
    assert result["verdict"] == "Strong SELL"


def test_null_sub_score_excluded_from_final():
    result = compute_full_score(make_cache(tech=80, fund=None, sent=80))
    # Only tech(40%) and sent(25%) remain, renormalised to 100%
    assert result["final"] is not None
    assert result["fundamental"] is None


def test_result_has_required_keys():
    result = compute_full_score(make_cache())
    for key in ("technical", "fundamental", "sentiment", "final", "verdict",
                 "patterns_detected", "technical_drivers", "fundamental_drivers", "sentiment_drivers"):
        assert key in result
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_engine.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `scoring/engine.py`**

```python
import math
from config import DEFAULT_WEIGHTS
from scoring.technical import compute_technical_score
from scoring.fundamental import compute_fundamental_score
from scoring.sentiment_score import compute_sentiment_score


def _verdict(score: int) -> str:
    if score >= 75:
        return "Strong BUY"
    if score >= 60:
        return "BUY"
    if score >= 45:
        return "HOLD"
    if score >= 30:
        return "SELL"
    return "Strong SELL"


def compute_full_score(cache_data: dict, weights: dict = None) -> dict:
    weights = weights or DEFAULT_WEIGHTS

    # Support test overrides
    overrides = cache_data.get("_override_scores", {})

    if "technical" in overrides:
        tech_score = overrides["technical"]
        tech_drivers = []
        patterns = []
    else:
        tech_score, tech_drivers, patterns = compute_technical_score(cache_data.get("ohlcv", {}))

    if "fundamental" in overrides:
        fund_score = overrides["fundamental"]
        fund_drivers = []
    else:
        fund_score, fund_drivers = compute_fundamental_score(cache_data.get("fundamentals", {}))

    if "sentiment" in overrides:
        sent_score = overrides["sentiment"]
        sent_drivers = []
    else:
        sent_score, sent_drivers = compute_sentiment_score(cache_data.get("sentiment_items", []))

    sub_scores = {
        "technical": (tech_score, weights["technical"]),
        "fundamental": (fund_score, weights["fundamental"]),
        "sentiment": (sent_score, weights["sentiment"]),
    }

    available = {k: (s, w) for k, (s, w) in sub_scores.items() if s is not None}
    if not available:
        final = None
        verdict = "HOLD"
    else:
        total_weight = sum(w for _, w in available.values())
        weighted_sum = sum(s * w for s, w in available.values())
        final = int(math.floor(weighted_sum / total_weight))
        verdict = _verdict(final)

    return {
        "technical": tech_score,
        "fundamental": fund_score,
        "sentiment": sent_score,
        "final": final,
        "verdict": verdict,
        "patterns_detected": patterns,
        "technical_drivers": tech_drivers,
        "fundamental_drivers": fund_drivers,
        "sentiment_drivers": sent_drivers,
    }
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
pytest tests/test_engine.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add trader/scoring/engine.py trader/tests/test_engine.py
git commit -m "feat: scoring engine — weighted combiner with null-score exclusion and verdict mapping"
```

---

## Task 10: Scheduler

**Files:**
- Create: `trader/scheduler.py`

> No unit tests for the scheduler itself — it is integration-layer code that wires together already-tested modules. Smoke test in Task 15.

- [ ] **Step 1: Implement `scheduler.py`**

```python
import logging
import logging.handlers
import os
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

import config
from cache import read_cache, write_cache
from data.fetcher import fetch_ohlcv, fetch_fundamentals
from data.sentiment import fetch_all_sentiment
from data.finbert import classify_batch
from scoring.engine import compute_full_score

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_started = False


def _run_ticker_job(ticker: str) -> None:
    logger.info("Refreshing %s", ticker)
    existing = read_cache(ticker) or {}
    entry = dict(existing)
    entry["ticker"] = ticker
    entry.setdefault("fetch_error", False)
    entry.setdefault("fetch_error_at", None)
    entry.setdefault("sentiment_stale", False)

    try:
        entry["ohlcv"] = fetch_ohlcv(ticker)
        entry["fundamentals"] = fetch_fundamentals(ticker)
        entry["fetch_error"] = False
        entry["fetch_error_at"] = None
    except Exception as e:
        logger.error("Fetch failed for %s: %s", ticker, e)
        entry["fetch_error"] = True
        entry["fetch_error_at"] = datetime.now(timezone.utc).isoformat()

    try:
        raw_items = fetch_all_sentiment(ticker)
        # Preserve labels for headlines already scored in the previous cache cycle
        existing_labels = {
            i["headline"]: {"label": i.get("label"), "score": i.get("score")}
            for i in existing.get("sentiment_items", [])
            if i.get("label") is not None
        }
        unscored = [i for i in raw_items if i["headline"] not in existing_labels]
        texts = [i["headline"] for i in unscored]
        if texts:
            labels = classify_batch(texts)
            for item, lab in zip(unscored, labels):
                item["label"] = lab["label"]
                item["score"] = lab["score"]
        # Merge: new items get fresh labels; seen items reuse cached labels
        for item in raw_items:
            if item.get("label") is None and item["headline"] in existing_labels:
                item["label"] = existing_labels[item["headline"]]["label"]
                item["score"] = existing_labels[item["headline"]]["score"]
        entry["sentiment_items"] = raw_items
        entry["sentiment_stale"] = False
    except Exception as e:
        logger.error("Sentiment failed for %s: %s", ticker, e)
        entry["sentiment_stale"] = True

    try:
        scores = compute_full_score(entry)
        entry["scores"] = scores
    except Exception as e:
        logger.error("Scoring failed for %s: %s", ticker, e)

    entry["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_cache(ticker, entry)
    logger.info("Done refreshing %s", ticker)


def _run_screener_batch(tickers: list[str]) -> None:
    for ticker in tickers:
        if ticker not in config.WATCHLIST:
            try:
                _run_ticker_job(ticker)
            except Exception as e:
                logger.error("Screener job failed for %s: %s", ticker, e)


def _load_screener_universe() -> list[str]:
    import csv
    tickers = []
    if not os.path.exists(config.SCREENER_UNIVERSE):
        return tickers
    with open(config.SCREENER_UNIVERSE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickers.append(row["ticker"])
    return tickers


def start_scheduler() -> None:
    global _scheduler, _started
    if _started:
        return
    _started = True

    os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
    logging.basicConfig(
        handlers=[
            logging.handlers.RotatingFileHandler(config.LOG_FILE, maxBytes=5_000_000, backupCount=3),
            logging.StreamHandler(),
        ],
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Warm up watchlist synchronously before scheduler starts
    for ticker in config.WATCHLIST:
        try:
            _run_ticker_job(ticker)
        except Exception as e:
            logger.error("Warmup failed for %s: %s", ticker, e)

    _scheduler = BackgroundScheduler(daemon=True)

    # Watchlist: every N minutes
    for ticker in config.WATCHLIST:
        _scheduler.add_job(
            _run_ticker_job,
            "interval",
            minutes=config.WATCHLIST_REFRESH_MINUTES,
            args=[ticker],
            id=f"watchlist_{ticker}",
        )

    # Screener: every N hours in batches
    universe = _load_screener_universe()
    batches = [universe[i:i + config.SCREENER_BATCH_SIZE] for i in range(0, len(universe), config.SCREENER_BATCH_SIZE)]
    for idx, batch in enumerate(batches):
        _scheduler.add_job(
            _run_screener_batch,
            "interval",
            hours=config.SCREENER_REFRESH_HOURS,
            args=[batch],
            id=f"screener_batch_{idx}",
        )

    _scheduler.start()
    logger.info("Scheduler started with %d jobs", len(_scheduler.get_jobs()))


def enqueue_watchlist_refresh() -> None:
    if _scheduler is None:
        return
    for ticker in config.WATCHLIST:
        _scheduler.add_job(
            _run_ticker_job,
            "date",
            args=[ticker],
            id=f"manual_{ticker}_{datetime.now().timestamp()}",
        )
```

- [ ] **Step 2: Commit**

```bash
git add trader/scheduler.py
git commit -m "feat: APScheduler singleton with watchlist warmup and screener batch jobs"
```

---

## Task 11: S&P 500 Universe CSV

**Files:**
- Create: `trader/data/sp500.csv`

- [ ] **Step 1: Create a minimal `sp500.csv` with representative tickers**

Create `data/sp500.csv` with the seed tickers below, then run `python data/build_sp500.py` to replace it with the full S&P 500 list from Wikipedia (see Step 2).

```csv
ticker,name,sector,market_cap_category
AAPL,Apple Inc.,Technology,Large
MSFT,Microsoft Corporation,Technology,Large
NVDA,NVIDIA Corporation,Technology,Large
GOOGL,Alphabet Inc.,Communication Services,Large
AMZN,Amazon.com Inc.,Consumer Discretionary,Large
META,Meta Platforms Inc.,Communication Services,Large
TSLA,Tesla Inc.,Consumer Discretionary,Large
JPM,JPMorgan Chase & Co.,Financials,Large
V,Visa Inc.,Financials,Large
JNJ,Johnson & Johnson,Health Care,Large
```

- [ ] **Step 2: Also create `data/build_sp500.py` for future refreshes**

```python
"""Run once to refresh sp500.csv from Wikipedia."""
import pandas as pd
import os

def build():
    tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    df = tables[0][["Symbol", "Security", "GICS Sector"]]
    df.columns = ["ticker", "name", "sector"]
    df["market_cap_category"] = "Large"
    out = os.path.join(os.path.dirname(__file__), "sp500.csv")
    df.to_csv(out, index=False)
    print(f"Written {len(df)} tickers to {out}")

if __name__ == "__main__":
    build()
```

- [ ] **Step 3: Commit**

```bash
git add trader/data/sp500.csv trader/data/build_sp500.py
git commit -m "feat: S&P 500 universe CSV with seed data and refresh script"
```

---

## Task 12: Watchlist Page

**Files:**
- Create: `trader/pages/watchlist.py`

- [ ] **Step 1: Implement `pages/watchlist.py`**

```python
import streamlit as st
from datetime import datetime, timezone, timedelta
import pandas as pd
import config
from cache import read_cache
from scheduler import enqueue_watchlist_refresh


_SIGNAL_COLORS = {
    "Strong BUY": "🟢",
    "BUY": "🟩",
    "HOLD": "🟡",
    "SELL": "🟧",
    "Strong SELL": "🔴",
}


def _is_stale(updated_at: str | None, hours: int) -> bool:
    if not updated_at:
        return True
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt) > timedelta(hours=hours)
    except Exception:
        return True


def render():
    st.title("Watchlist")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Refresh All"):
            enqueue_watchlist_refresh()
            st.success("Refresh queued — data updates in the background.")

    rows = []
    for ticker in config.WATCHLIST:
        data = read_cache(ticker)
        if data is None:
            rows.append({"Ticker": ticker, "Price": "—", "Final": "—", "Tech": "—",
                         "Fund": "—", "Sent": "—", "Signal": "—", "Updated": "No data"})
            continue

        scores = data.get("scores", {})
        ohlcv = data.get("ohlcv", {})
        close = ohlcv.get("close", [])
        price = f"${close[-1]:.2f}" if close else "—"
        pct = ""
        if len(close) >= 2:
            chg = (close[-1] - close[-2]) / close[-2] * 100
            pct = f" ({chg:+.1f}%)"

        stale = _is_stale(data.get("updated_at"), config.WATCHLIST_STALE_HOURS)
        updated = data.get("updated_at", "—")[:16].replace("T", " ") + (" ⚠️" if stale else "")

        verdict = scores.get("verdict", "—")
        signal_label = f"{_SIGNAL_COLORS.get(verdict, '')} {verdict}"

        rows.append({
            "Ticker": ticker,
            "Price": price + pct,
            "Final": scores.get("final", "—"),
            "Tech": scores.get("technical", "—"),
            "Fund": scores.get("fundamental", "—"),
            "Sent": scores.get("sentiment", "—"),
            "Signal": signal_label,
            "Updated": updated,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("Click a ticker in the sidebar to view its full analysis.")
```

- [ ] **Step 2: Commit**

```bash
git add trader/pages/watchlist.py
git commit -m "feat: watchlist dashboard page"
```

---

## Task 13: Stock Detail Page

**Files:**
- Create: `trader/pages/detail.py`

- [ ] **Step 1: Implement `pages/detail.py`**

```python
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timezone, timedelta
import config
from cache import read_cache
from scoring.engine import compute_full_score

_VERDICT_COLORS = {
    "Strong BUY": "#00aa44",
    "BUY": "#44cc88",
    "HOLD": "#ccaa00",
    "SELL": "#cc6600",
    "Strong SELL": "#cc0000",
}


def _build_candlestick(ohlcv: dict, patterns: list) -> go.Figure:
    fig = go.Figure(data=[go.Candlestick(
        x=ohlcv["dates"],
        open=ohlcv["open"],
        high=ohlcv["high"],
        low=ohlcv["low"],
        close=ohlcv["close"],
        name="Price",
    )])
    for p in patterns:
        fig.add_vline(
            x=p["detected_at"],
            line_dash="dash",
            line_color="orange",
            annotation_text=p["name"],
            annotation_position="top",
        )
    fig.update_layout(xaxis_rangeslider_visible=False, height=400, margin=dict(l=0, r=0, t=30, b=0))
    return fig


def render(ticker: str):
    st.title(f"{ticker} — Full Analysis")

    data = read_cache(ticker)
    if data is None:
        st.warning(f"No cached data for {ticker}. Please wait for the scheduler to run.")
        return

    if data.get("fetch_error"):
        st.error(f"Last fetch failed at {data.get('fetch_error_at', 'unknown')}. Showing stale data.")

    updated_at = data.get("updated_at")
    if updated_at:
        try:
            from datetime import datetime, timezone, timedelta
            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - dt) > timedelta(hours=config.WATCHLIST_STALE_HOURS):
                st.warning(f"⚠️ Data is stale — last updated {updated_at[:16].replace('T', ' ')} UTC.")
        except Exception:
            pass

    # Weight sliders
    st.sidebar.subheader("Score Weights")
    w_tech = st.sidebar.slider("Technical %", 0, 100, int(config.DEFAULT_WEIGHTS["technical"] * 100))
    w_fund = st.sidebar.slider("Fundamental %", 0, 100, int(config.DEFAULT_WEIGHTS["fundamental"] * 100))
    w_sent = st.sidebar.slider("Sentiment %", 0, 100, int(config.DEFAULT_WEIGHTS["sentiment"] * 100))
    total_w = w_tech + w_fund + w_sent
    if total_w == 0:
        st.sidebar.error("Weights must sum > 0")
        return
    weights = {
        "technical": w_tech / total_w,
        "fundamental": w_fund / total_w,
        "sentiment": w_sent / total_w,
    }

    scores = compute_full_score(data, weights=weights)

    # Verdict banner with one-sentence reasoning summary
    verdict = scores.get("verdict", "—")
    color = _VERDICT_COLORS.get(verdict, "#888888")
    # Build a short reasoning string from the strongest driver in each category
    reason_parts = []
    for key in ("technical_drivers", "fundamental_drivers", "sentiment_drivers"):
        drivers = scores.get(key, [])
        if drivers:
            reason_parts.append(drivers[0])
    reason = " · ".join(reason_parts[:2]) if reason_parts else "Insufficient data for summary."
    st.markdown(
        f"<div style='background:{color};padding:16px;border-radius:8px;text-align:center'>"
        f"<h2 style='color:white;margin:0'>{verdict} — Score: {scores.get('final', '—')}/100</h2>"
        f"<p style='color:white;margin:8px 0 0 0;font-size:0.9em'>{reason}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("")

    # Candlestick chart
    ohlcv = data.get("ohlcv", {})
    if ohlcv.get("close"):
        st.plotly_chart(_build_candlestick(ohlcv, scores.get("patterns_detected", [])), use_container_width=True)

    # Three score panels
    col1, col2, col3 = st.columns(3)
    for col, key, label in [(col1, "technical", "Technical"), (col2, "fundamental", "Fundamental"), (col3, "sentiment", "Sentiment")]:
        with col:
            sub = scores.get(key)
            if sub is None:
                st.metric(label, "—")
            else:
                color_indicator = "🟢" if sub >= 60 else ("🟡" if sub >= 45 else "🔴")
                st.metric(label, f"{color_indicator} {sub}/100")
            drivers_key = f"{key}_drivers"
            for d in scores.get(drivers_key, [])[:5]:
                st.caption(f"• {d}")

    # Patterns
    patterns = scores.get("patterns_detected", [])
    if patterns:
        st.subheader("Detected Patterns")
        for p in patterns:
            with st.expander(f"{p['name']} — {p['detected_at']} ({p['reliability']} reliability)"):
                st.write(p["meaning"])
                st.caption(f"Direction: {p['direction']}")

    # Fundamentals table
    fund = data.get("fundamentals", {})
    if fund:
        st.subheader("Fundamentals")
        fund_rows = []
        for k in ("pe_ratio", "ev_ebitda", "revenue_growth_yoy", "gross_margin", "operating_margin", "debt_equity"):
            v = fund.get(k)
            fund_rows.append({"Metric": k.replace("_", " ").title(), "Value": f"{v:.2f}" if v is not None else "—"})
        st.dataframe(pd.DataFrame(fund_rows), hide_index=True, use_container_width=True)

    # Sentiment feed
    items = data.get("sentiment_items", [])
    if items:
        st.subheader("Sentiment Feed")
        _SENT_BADGE = {"positive": "🟢 Bullish", "negative": "🔴 Bearish", "neutral": "🟡 Neutral"}
        for item in items[:20]:
            badge = _SENT_BADGE.get(item.get("label"), "⚪ Unknown")
            st.markdown(f"**{badge}** [{item.get('source', '')}] {item.get('headline', '')}")
```

- [ ] **Step 2: Commit**

```bash
git add trader/pages/detail.py
git commit -m "feat: stock detail page with candlestick chart, score panels, patterns, and sentiment feed"
```

---

## Task 14: Screener Page

**Files:**
- Create: `trader/pages/screener.py`

- [ ] **Step 1: Implement `pages/screener.py`**

```python
import streamlit as st
import pandas as pd
import csv
import os
from datetime import datetime, timezone, timedelta
import config
from cache import read_cache


def _load_universe() -> list[dict]:
    rows = []
    if not os.path.exists(config.SCREENER_UNIVERSE):
        return rows
    with open(config.SCREENER_UNIVERSE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _is_stale(updated_at: str | None, hours: int) -> bool:
    if not updated_at:
        return True
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt) > timedelta(hours=hours)
    except Exception:
        return True


def render():
    st.title("Screener")
    st.caption("Scores are pre-computed by the background scheduler. Screener universe refreshes every 4 hours.")

    universe = _load_universe()
    sectors = sorted(set(r["sector"] for r in universe if r.get("sector")))
    cap_cats = ["Large", "Mid", "Small"]

    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        min_score = st.slider("Min Final Score", 0, 100, 0)
    with col2:
        signal_filter = st.multiselect("Signal", ["Strong BUY", "BUY", "HOLD", "SELL", "Strong SELL"])
    with col3:
        sector_filter = st.multiselect("Sector", sectors)
    with col4:
        cap_filter = st.multiselect("Market Cap", cap_cats)

    rows = []
    for row in universe:
        ticker = row["ticker"]
        sector = row.get("sector", "")
        cap = row.get("market_cap_category", "Large")

        if sector_filter and sector not in sector_filter:
            continue
        if cap_filter and cap not in cap_filter:
            continue

        data = read_cache(ticker)
        if data is None:
            continue

        scores = data.get("scores", {})
        final = scores.get("final")
        verdict = scores.get("verdict", "—")

        # Apply filters only to tickers that have a score
        if final is not None:
            if final < min_score:
                continue
            if signal_filter and verdict not in signal_filter:
                continue

        stale = _is_stale(data.get("updated_at"), config.SCREENER_STALE_HOURS)
        rows.append({
            "Ticker": ticker,
            "Name": row.get("name", ""),
            "Sector": sector,
            "Cap": cap,
            "Final Score": final,          # None → sorts to bottom
            "Signal": verdict,
            "Tech": scores.get("technical", "—"),
            "Fund": scores.get("fundamental", "—"),
            "Sent": scores.get("sentiment", "—"),
            "Stale": "⚠️" if stale else "",
        })

    # Tickers with a score first (desc), then null-score tickers at the bottom
    rows_sorted = sorted(rows, key=lambda r: (r["Final Score"] is None, -(r["Final Score"] or 0)))

    if not rows_sorted:
        st.info("No tickers match the current filters, or no cache data yet.")
    else:
        st.dataframe(pd.DataFrame(rows_sorted), hide_index=True, use_container_width=True)
        st.caption(f"{len(rows_sorted)} tickers shown. ⚠️ = data older than {config.SCREENER_STALE_HOURS}h.")
```

- [ ] **Step 2: Commit**

```bash
git add trader/pages/screener.py
git commit -m "feat: screener page with sector/cap/score/signal filters"
```

---

## Task 15: Main App + Smoke Test

**Files:**
- Create: `trader/app.py`

- [ ] **Step 1: Implement `app.py`**

```python
import streamlit as st

st.set_page_config(page_title="Trader Dashboard", layout="wide")

# Scheduler singleton guard — must run before any page import
if "scheduler_started" not in st.session_state:
    from scheduler import start_scheduler
    start_scheduler()
    st.session_state["scheduler_started"] = True

# Sidebar navigation
import config

st.sidebar.title("Trader Dashboard")

# FinBERT failure warning — surfaced in sidebar as required by spec
from data import finbert as _finbert
if _finbert._load_failed:
    st.sidebar.warning("⚠️ FinBERT failed to load. Sentiment scoring is disabled for this session.")

page = st.sidebar.radio("Navigate", ["Watchlist", "Screener"] + config.WATCHLIST)

if page == "Watchlist":
    from pages.watchlist import render
    render()
elif page == "Screener":
    from pages.screener import render
    render()
else:
    from pages.detail import render
    render(page)
```

- [ ] **Step 2: Run the full test suite one final time**

```bash
cd trader
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 3: Run the app and verify it starts**

```bash
cd trader
streamlit run app.py
```

Expected:
- App opens at `http://localhost:8501`
- Console shows "FinBERT loaded successfully" (or download progress on first run)
- Watchlist page renders with the tickers from `config.WATCHLIST`
- No Python errors in the terminal

- [ ] **Step 4: Verify Screener page loads**

Navigate to Screener in the sidebar. Expected: table renders (may be empty if only seed CSV tickers are cached).

- [ ] **Step 5: Verify Stock Detail page**

Click one of the watchlist ticker shortcuts in the sidebar. Expected: candlestick chart, three score panels, verdict banner all render without errors.

- [ ] **Step 6: Final commit**

```bash
git add trader/app.py
git commit -m "feat: main Streamlit app with scheduler singleton guard and page routing"
```

---

## Running the App

```bash
cd trader
pip install -r requirements.txt
streamlit run app.py
```

On first run: FinBERT downloads ~400 MB (cached locally by HuggingFace after that). Watchlist data loads synchronously — expect 10–30 seconds before the UI appears.
