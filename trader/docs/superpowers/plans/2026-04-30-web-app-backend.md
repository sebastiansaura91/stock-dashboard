# Stock Dashboard — Web App Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit app with a FastAPI REST API backed by Supabase and HuggingFace Inference API, reusing all existing Python scoring logic unchanged.

**Architecture:** FastAPI app in `trader/api/` exposes REST endpoints. `cache.py` is replaced with a Supabase client keeping the same `read_cache`/`write_cache` interface. `data/finbert.py` is replaced with an HTTP client to HuggingFace Inference API keeping the same `classify_batch` interface. `scheduler.py` is rewritten without the Streamlit dependency. All scoring modules (`scoring/`) remain untouched.

**Tech Stack:** Python 3.11+, FastAPI 0.110+, uvicorn, supabase-py 2.x, httpx, APScheduler 3.x, Railway (hosting)

**⚠️ Note on running tests:** Python is not available on the development machine (Windows Store stubs). Tests are written correctly and can be run in any Python 3.11+ environment with `pytest trader/`. On this machine, correctness is verified by the spec/quality review subagents reading source.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `trader/config.py` | Modify | Add Supabase + HF env-var constants |
| `trader/requirements.txt` | Replace | API dependencies (removes Streamlit/torch/portalocker) |
| `trader/cache.py` | Replace | Supabase client — tickers table + watchlist table |
| `trader/data/finbert.py` | Replace | HF Inference API HTTP client, same `classify_batch` interface |
| `trader/scheduler.py` | Replace | APScheduler singleton, no Streamlit dependency |
| `trader/api/__init__.py` | Create | Package marker |
| `trader/api/main.py` | Create | FastAPI app, CORS, lifespan (scheduler start/stop) |
| `trader/api/routers/__init__.py` | Create | Package marker |
| `trader/api/routers/watchlist.py` | Create | GET/POST/DELETE /api/watchlist |
| `trader/api/routers/stock.py` | Create | GET /api/stock/{ticker} |
| `trader/api/routers/screener.py` | Create | GET /api/screener |
| `trader/Procfile` | Create | Railway process definition |
| `trader/.env.example` | Create | Environment variable template |
| `trader/tests/test_cache_supabase.py` | Create | Tests for new cache.py (mocked Supabase) |
| `trader/tests/test_finbert_api.py` | Create | Tests for new finbert.py (mocked httpx) |
| `trader/tests/test_api.py` | Create | FastAPI endpoint tests (TestClient) |

---

## Task 1: Config + Requirements

**Files:**
- Modify: `trader/config.py`
- Replace: `trader/requirements.txt`
- Create: `trader/.env.example`

- [ ] **Step 1: Add env-var constants to config.py**

Append to the bottom of `trader/config.py`:

```python
# Supabase (read from environment — never hardcode)
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# HuggingFace Inference API
HF_API_KEY: str = os.getenv("HF_API_KEY", "")
HF_API_URL: str = os.getenv(
    "HF_API_URL",
    "https://api-inference.huggingface.co/models/ProsusAI/finbert",
)
```

- [ ] **Step 2: Replace requirements.txt**

Write `trader/requirements.txt` with API dependencies (Streamlit, torch, transformers, portalocker, pywebview removed):

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
supabase>=2.4.0
httpx>=0.26.0
python-dotenv>=1.0.0
yfinance>=0.2.40
pandas-ta>=0.3.14b
APScheduler>=3.10.0,<4.0
feedparser>=6.0.11
requests>=2.31.0
beautifulsoup4>=4.12.0
scipy>=1.13.0
numpy>=1.26.0
pandas>=2.2.0
lxml>=5.0.0
pytest>=8.0.0
pytest-mock>=3.14.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 3: Create .env.example**

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
HF_API_KEY=hf_your_huggingface_token
HF_API_URL=https://api-inference.huggingface.co/models/ProsusAI/finbert
```

- [ ] **Step 4: Commit**

```bash
git add trader/config.py trader/requirements.txt trader/.env.example
git commit -m "feat: add Supabase + HF API config; update requirements for FastAPI"
```

---

## Task 2: Supabase Setup + New cache.py

**Context:** The current `cache.py` uses portalocker + local JSON files. Replace it with Supabase. Keep the exact same `read_cache(ticker, cache_dir=None)` and `write_cache(ticker, data, cache_dir=None)` signatures so all existing callers (`scheduler.py`, `scoring/fundamental.py`) work without changes. Add watchlist CRUD functions.

**Supabase SQL — run once in the Supabase SQL editor:**

```sql
-- Ticker cache
create table if not exists tickers (
  ticker      text primary key,
  data        jsonb not null,
  updated_at  timestamptz default now()
);

-- Watchlist
create table if not exists watchlist (
  ticker    text primary key,
  added_at  timestamptz default now()
);

-- Seed default watchlist tickers
insert into watchlist (ticker) values ('AAPL'), ('MSFT'), ('NVDA')
  on conflict do nothing;
```

**Files:**
- Replace: `trader/cache.py`
- Create: `trader/tests/test_cache_supabase.py`

- [ ] **Step 1: Write the failing tests**

Create `trader/tests/test_cache_supabase.py`:

```python
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


def test_remove_watchlist_ticker_calls_delete():
    with patch("cache._get_client") as mock_get:
        client = _mock_client()
        mock_get.return_value = client
        from cache import remove_watchlist_ticker
        remove_watchlist_ticker("TSLA")
    client.table.return_value.delete.return_value.eq.assert_called_with("ticker", "TSLA")
```

- [ ] **Step 2: Verify tests fail (code review — Python not runnable on this machine)**

Read the test file and confirm it would fail because the new `cache.py` functions don't exist yet.

- [ ] **Step 3: Implement the new cache.py**

Replace `trader/cache.py` entirely:

```python
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
```

- [ ] **Step 4: Verify tests pass (code review)**

Read `test_cache_supabase.py` and `cache.py` together. Confirm:
- `_mock_client` chain matches actual Supabase call patterns in the implementation
- `read_cache` reads from `result.data[0]["data"]` and returns `None` on empty list
- `write_cache` upserts with `ticker.upper()` and an `updated_at` timestamp
- `get_watchlist_tickers` extracts `row["ticker"]` from each row
- `add_watchlist_ticker` calls `insert` on the watchlist table
- `remove_watchlist_ticker` calls `delete().eq("ticker", ticker.upper())`

- [ ] **Step 5: Commit**

```bash
git add trader/cache.py trader/tests/test_cache_supabase.py
git commit -m "feat: replace file cache with Supabase (same read_cache/write_cache interface)"
```

---

## Task 3: HuggingFace Inference API Client

**Context:** Replace the local FinBERT model (`data/finbert.py`) with an HTTP client to the HuggingFace Inference API. Keep the exact same `classify_batch(texts)` interface.

**HF API behaviour:**
- POST `https://api-inference.huggingface.co/models/ProsusAI/finbert`
- Body: `{"inputs": ["text1", "text2"]}` (list of strings)
- Response: `[[{"label": "positive", "score": 0.9}, ...], [...]]` — one list per input, sorted by score descending
- Label values from this model: `"positive"`, `"negative"`, `"neutral"` (lowercase, confirmed)
- On model loading (cold start): returns `{"error": "...", "estimated_time": N}` with HTTP 503 — wait and retry once

**Files:**
- Replace: `trader/data/finbert.py`
- Create: `trader/tests/test_finbert_api.py`

- [ ] **Step 1: Write the failing tests**

Create `trader/tests/test_finbert_api.py`:

```python
from unittest.mock import patch, MagicMock


def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx
        mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock
        )
    return mock


def test_classify_batch_returns_correct_labels():
    hf_response = [
        [{"label": "positive", "score": 0.9}, {"label": "negative", "score": 0.05}, {"label": "neutral", "score": 0.05}],
        [{"label": "negative", "score": 0.8}, {"label": "positive", "score": 0.1}, {"label": "neutral", "score": 0.1}],
    ]
    with patch("data.finbert.httpx.post", return_value=_mock_response(hf_response)):
        from data.finbert import classify_batch
        results = classify_batch(["Good news", "Bad news"])
    assert len(results) == 2
    assert results[0]["label"] == "positive"
    assert results[1]["label"] == "negative"
    assert 0.0 <= results[0]["score"] <= 1.0


def test_classify_batch_empty_returns_empty():
    from data.finbert import classify_batch
    assert classify_batch([]) == []


def test_classify_batch_falls_back_on_error():
    with patch("data.finbert.httpx.post", side_effect=Exception("network error")):
        from data.finbert import classify_batch
        results = classify_batch(["some text"])
    assert len(results) == 1
    assert results[0]["label"] == "neutral"
    assert results[0]["score"] == 0.0


def test_classify_batch_retries_on_503():
    """On HTTP 503 (model loading), sleep and retry once."""
    loading_response = _mock_response({"error": "loading", "estimated_time": 5}, 503)
    success_response = _mock_response(
        [[{"label": "neutral", "score": 0.9}, {"label": "positive", "score": 0.05}, {"label": "negative", "score": 0.05}]],
        200,
    )
    with patch("data.finbert.httpx.post", side_effect=[loading_response, success_response]):
        with patch("data.finbert.time.sleep"):
            from data.finbert import classify_batch
            results = classify_batch(["hello"])
    assert results[0]["label"] == "neutral"
```

- [ ] **Step 2: Verify tests fail (code review)**

Confirm the test file references functions/behaviours not yet in `data/finbert.py`.

- [ ] **Step 3: Implement the new data/finbert.py**

Replace `trader/data/finbert.py` entirely:

```python
"""HuggingFace Inference API client for FinBERT sentiment classification.

Replaces the local transformers pipeline with HTTP calls to the free
HuggingFace Inference API. Keeps the same classify_batch() interface
so callers (scheduler.py) work without modification.
"""

import logging
import time

import httpx

from config import HF_API_KEY, HF_API_URL, FINBERT_BATCH_SIZE

logger = logging.getLogger(__name__)

_NEUTRAL_FALLBACK = {"label": "neutral", "score": 0.0}


def classify_batch(texts: list[str]) -> list[dict]:
    """Classify *texts* using the HuggingFace Inference API.

    Returns a list of {"label": str, "score": float} dicts — one per input.
    Falls back to neutral on any error so callers never crash.
    """
    if not texts:
        return []

    results: list[dict] = []
    for i in range(0, len(texts), FINBERT_BATCH_SIZE):
        chunk = texts[i : i + FINBERT_BATCH_SIZE]
        results.extend(_classify_chunk(chunk))

    # Safety: ensure count matches (should never differ, but guard it)
    if len(results) != len(texts):
        logger.error(
            "classify_batch: result count mismatch %d vs %d",
            len(results),
            len(texts),
        )
        while len(results) < len(texts):
            results.append(dict(_NEUTRAL_FALLBACK))

    return results[: len(texts)]


def _classify_chunk(texts: list[str]) -> list[dict]:
    """Send one batch to the HF API and parse the response."""
    headers = {}
    if HF_API_KEY:
        headers["Authorization"] = f"Bearer {HF_API_KEY}"

    try:
        response = httpx.post(
            HF_API_URL,
            headers=headers,
            json={"inputs": texts},
            timeout=30.0,
        )
    except Exception:
        logger.exception("HF API request failed")
        return [dict(_NEUTRAL_FALLBACK) for _ in texts]

    # 503 = model still loading — wait once and retry
    if response.status_code == 503:
        body = response.json()
        wait = min(float(body.get("estimated_time", 20)), 60.0)
        logger.warning("HF model loading — waiting %.0fs then retrying", wait)
        time.sleep(wait)
        try:
            response = httpx.post(
                HF_API_URL,
                headers=headers,
                json={"inputs": texts},
                timeout=30.0,
            )
        except Exception:
            logger.exception("HF API retry failed")
            return [dict(_NEUTRAL_FALLBACK) for _ in texts]

    try:
        response.raise_for_status()
        raw = response.json()
    except Exception:
        logger.exception("HF API response error (status %d)", response.status_code)
        return [dict(_NEUTRAL_FALLBACK) for _ in texts]

    if not isinstance(raw, list):
        logger.error("Unexpected HF API response type: %s", type(raw))
        return [dict(_NEUTRAL_FALLBACK) for _ in texts]

    results = []
    for item in raw:
        if isinstance(item, list) and item:
            best = max(item, key=lambda x: x.get("score", 0.0))
            results.append(
                {
                    "label": best.get("label", "neutral").lower(),
                    "score": float(best.get("score", 0.0)),
                }
            )
        else:
            results.append(dict(_NEUTRAL_FALLBACK))

    return results
```

- [ ] **Step 4: Verify tests pass (code review)**

Read both files and confirm the logic matches each test scenario.

- [ ] **Step 5: Commit**

```bash
git add trader/data/finbert.py trader/tests/test_finbert_api.py
git commit -m "feat: replace local FinBERT with HuggingFace Inference API client"
```

---

## Task 4: Scheduler Rewrite (Remove Streamlit Dependency)

**Context:** `scheduler.py` currently uses `st.session_state` for singleton management. Rewrite it with a module-level singleton + threading.Lock (same pattern as `data/finbert.py` used to have). The `refresh_ticker` logic is unchanged. Replace per-ticker jobs with a single job that reads the live watchlist from Supabase.

**Files:**
- Replace: `trader/scheduler.py`
- Create: `trader/tests/test_scheduler_api.py`

- [ ] **Step 1: Write the failing tests**

Create `trader/tests/test_scheduler_api.py`:

```python
from unittest.mock import patch, MagicMock


def test_get_scheduler_returns_singleton():
    import importlib
    import scheduler as sched_mod
    # Reset singleton for test isolation
    sched_mod._scheduler = None
    s1 = sched_mod.get_scheduler()
    s2 = sched_mod.get_scheduler()
    assert s1 is s2


def test_start_scheduler_adds_job_and_starts():
    import scheduler as sched_mod
    mock_scheduler = MagicMock()
    mock_scheduler.running = False
    with patch.object(sched_mod, "get_scheduler", return_value=mock_scheduler):
        sched_mod.start_scheduler()
    mock_scheduler.add_job.assert_called_once()
    mock_scheduler.start.assert_called_once()


def test_stop_scheduler_calls_shutdown():
    import scheduler as sched_mod
    mock_scheduler = MagicMock()
    mock_scheduler.running = True
    with patch.object(sched_mod, "get_scheduler", return_value=mock_scheduler):
        sched_mod.stop_scheduler()
    mock_scheduler.shutdown.assert_called_once_with(wait=False)


def test_refresh_ticker_writes_cache_on_success():
    with (
        patch("scheduler.fetch_ohlcv", return_value={"close": [100.0]}),
        patch("scheduler.fetch_fundamentals", return_value={}),
        patch("scheduler.fetch_all_sentiment", return_value=[]),
        patch("scheduler.write_cache") as mock_write,
    ):
        from scheduler import refresh_ticker
        refresh_ticker("AAPL")
    mock_write.assert_called_once()
    call_args = mock_write.call_args[0]
    assert call_args[0] == "AAPL"
    assert "ohlcv" in call_args[1]
    assert "fetched_at" in call_args[1]
```

- [ ] **Step 2: Verify tests fail (code review)**

Confirm `get_scheduler()` doesn't exist yet (current scheduler uses `st.session_state`).

- [ ] **Step 3: Implement the new scheduler.py**

Replace `trader/scheduler.py` entirely:

```python
"""Background scheduler for periodic ticker data refresh.

Rewrite of the original Streamlit-dependent scheduler.
Uses a module-level singleton (threading.Lock, double-checked) instead of
st.session_state so it runs correctly inside FastAPI.
"""

import logging
import threading
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from cache import write_cache
from config import WATCHLIST_REFRESH_MINUTES
from data.fetcher import fetch_fundamentals, fetch_ohlcv
from data.finbert import classify_batch
from data.sentiment import fetch_all_sentiment

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()


def get_scheduler() -> BackgroundScheduler:
    """Return the shared BackgroundScheduler singleton (lazy init)."""
    global _scheduler
    if _scheduler is None:
        with _lock:
            if _scheduler is None:
                _scheduler = BackgroundScheduler(daemon=True)
    return _scheduler


# ---------------------------------------------------------------------------
# Core refresh logic (unchanged from original)
# ---------------------------------------------------------------------------

def refresh_ticker(ticker: str) -> None:
    """Fetch fresh data for *ticker* and write it to cache.

    All exceptions are caught so a transient error never crashes the thread.
    """
    try:
        ohlcv = fetch_ohlcv(ticker)
        fundamentals = fetch_fundamentals(ticker)
        sentiment_items = fetch_all_sentiment(ticker)

        unlabelled_indices = [
            i for i, item in enumerate(sentiment_items)
            if not item.get("label")
        ]
        if unlabelled_indices:
            headlines = [sentiment_items[i]["headline"] for i in unlabelled_indices]
            classifications = classify_batch(headlines)
            if len(classifications) != len(headlines):
                logger.warning(
                    "refresh_ticker: classify_batch length mismatch %d vs %d (%s)",
                    len(classifications), len(headlines), ticker,
                )
            for idx, classification in zip(unlabelled_indices, classifications):
                sentiment_items[idx]["label"] = classification["label"]
                sentiment_items[idx]["score"] = classification["score"]

        cache_data = {
            "ohlcv": ohlcv,
            "fundamentals": fundamentals,
            "sentiment_items": sentiment_items,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        write_cache(ticker, cache_data)
        logger.info("refresh_ticker: %s updated", ticker)
    except Exception:
        logger.exception("refresh_ticker: error refreshing %s", ticker)


def _refresh_all() -> None:
    """Job target: refresh every ticker currently in the watchlist."""
    from cache import get_watchlist_tickers
    for ticker in get_watchlist_tickers():
        refresh_ticker(ticker)


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------

def start_scheduler() -> None:
    """Start the singleton scheduler with a single watchlist-refresh job."""
    scheduler = get_scheduler()
    scheduler.add_job(
        func=_refresh_all,
        trigger=IntervalTrigger(minutes=WATCHLIST_REFRESH_MINUTES),
        id="refresh_all",
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()
        logger.info("start_scheduler: scheduler started")


def stop_scheduler() -> None:
    """Stop the scheduler (non-blocking)."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("stop_scheduler: scheduler stopped")


def refresh_ticker_now(ticker: str) -> None:
    """Synchronously refresh one ticker (on-demand from API)."""
    refresh_ticker(ticker)
```

- [ ] **Step 4: Verify tests pass (code review)**

Confirm `get_scheduler` returns a singleton, `start_scheduler` calls `add_job` + `start`, `stop_scheduler` calls `shutdown(wait=False)`, and `refresh_ticker` builds the correct cache dict.

- [ ] **Step 5: Commit**

```bash
git add trader/scheduler.py trader/tests/test_scheduler_api.py
git commit -m "feat: rewrite scheduler without Streamlit — module-level singleton, single refresh-all job"
```

---

## Task 5: FastAPI App Scaffold

**Files:**
- Create: `trader/api/__init__.py`
- Create: `trader/api/main.py`
- Create: `trader/api/routers/__init__.py`
- Create: `trader/Procfile`

- [ ] **Step 1: Write failing test**

Add to `trader/tests/test_api.py`:

```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Verify test fails (code review)**

`api/main.py` doesn't exist yet.

- [ ] **Step 3: Create the files**

`trader/api/__init__.py` — empty

`trader/api/routers/__init__.py` — empty

`trader/api/main.py`:

```python
"""FastAPI application entry point.

Starts the APScheduler background scheduler on startup and shuts it down
cleanly when the app exits.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    logger.info("Application startup complete")
    yield
    stop_scheduler()
    logger.info("Application shutdown complete")


app = FastAPI(title="Stock Dashboard API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restrict to Vercel domain in Railway env vars if desired
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers are imported here (after app is created to avoid circular imports)
from api.routers import watchlist, stock, screener  # noqa: E402

app.include_router(watchlist.router, prefix="/api")
app.include_router(stock.router, prefix="/api")
app.include_router(screener.router, prefix="/api")


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}
```

`trader/Procfile`:

```
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 4: Verify test passes (code review)**

Confirm `GET /api/health` returns `{"status": "ok"}` with 200.

- [ ] **Step 5: Commit**

```bash
git add trader/api/ trader/Procfile
git commit -m "feat: FastAPI app scaffold with health endpoint and CORS"
```

---

## Task 6: Watchlist Router

**Files:**
- Create: `trader/api/routers/watchlist.py`
- Modify: `trader/tests/test_api.py` (add watchlist tests)

- [ ] **Step 1: Write failing tests**

Append to `trader/tests/test_api.py`:

```python
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
```

- [ ] **Step 2: Verify tests fail (code review)**

`api/routers/watchlist.py` doesn't exist yet.

- [ ] **Step 3: Implement watchlist router**

Create `trader/api/routers/watchlist.py`:

```python
"""Watchlist API router.

GET  /api/watchlist        — scores for all watchlist tickers
POST /api/watchlist        — add a ticker (body: {"ticker": "AAPL"})
DELETE /api/watchlist/{t}  — remove a ticker
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from cache import (
    add_watchlist_ticker,
    get_watchlist_tickers,
    read_cache,
    remove_watchlist_ticker,
)
from scoring.engine import compute_full_score

logger = logging.getLogger(__name__)
router = APIRouter()


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("/watchlist")
def get_watchlist() -> list[dict]:
    tickers = get_watchlist_tickers()
    results = []
    for ticker in tickers:
        data = read_cache(ticker)
        if data:
            scores = compute_full_score(data)
            close = data.get("ohlcv", {}).get("close", [])
            results.append(
                {
                    "ticker": ticker,
                    "company": data.get("fundamentals", {}).get("company_name", ticker),
                    "price": round(close[-1], 2) if close else None,
                    "final_score": scores["final"],
                    "verdict": scores["verdict"],
                    "updated_at": data.get("fetched_at"),
                }
            )
        else:
            results.append(
                {
                    "ticker": ticker,
                    "company": ticker,
                    "price": None,
                    "final_score": None,
                    "verdict": "HOLD",
                    "updated_at": None,
                }
            )
    return results


@router.post("/watchlist")
def add_ticker(body: AddTickerRequest, background_tasks: BackgroundTasks) -> dict:
    ticker = body.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")
    add_watchlist_ticker(ticker)
    background_tasks.add_task(_fetch_ticker_background, ticker)
    return {"ticker": ticker, "status": "added"}


@router.delete("/watchlist/{ticker}")
def remove_ticker(ticker: str) -> dict:
    remove_watchlist_ticker(ticker.upper())
    return {"ticker": ticker.upper(), "status": "removed"}


def _fetch_ticker_background(ticker: str) -> None:
    """Background task: fetch + cache data for a newly added ticker."""
    from scheduler import refresh_ticker_now
    refresh_ticker_now(ticker)
```

- [ ] **Step 4: Verify tests pass (code review)**

Confirm mock chains match implementation call patterns.

- [ ] **Step 5: Commit**

```bash
git add trader/api/routers/watchlist.py trader/tests/test_api.py
git commit -m "feat: watchlist router (GET/POST/DELETE /api/watchlist)"
```

---

## Task 7: Stock Detail Router

**Files:**
- Create: `trader/api/routers/stock.py`
- Modify: `trader/tests/test_api.py` (add stock tests)

- [ ] **Step 1: Write failing tests**

Append to `trader/tests/test_api.py`:

```python
def test_get_stock_returns_full_analysis():
    mock_cache = {
        "ohlcv": {"close": [150.0], "open": [148.0], "high": [151.0],
                  "low": [147.0], "volume": [1000000], "dates": ["2026-04-30"]},
        "fundamentals": {
            "company_name": "Apple Inc", "pe_ratio": 25.0,
            "ev_ebitda": 15.0, "revenue_growth_yoy": 0.12,
            "gross_margin": 0.45, "operating_margin": 0.30,
            "debt_equity": 1.5, "sector": "Technology", "missing_fields": [],
        },
        "sentiment_items": [],
        "fetched_at": "2026-04-30T00:00:00+00:00",
        "_override_scores": {"technical": 70, "fundamental": 65, "sentiment": 60},
    }
    with patch("cache.read_cache", return_value=mock_cache):
        response = client.get("/api/stock/AAPL")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert "technical_score" in body
    assert "fundamental_score" in body
    assert "sentiment_score" in body
    assert "final_score" in body
    assert "verdict" in body
    assert "ohlcv" in body
    assert "patterns" in body
    assert "technical_drivers" in body
    assert "fundamental_drivers" in body
    assert "sentiment_drivers" in body
    assert "fundamentals" in body


def test_get_stock_not_found_returns_404():
    with patch("cache.read_cache", return_value=None):
        response = client.get("/api/stock/FAKE")
    assert response.status_code == 404
```

- [ ] **Step 2: Verify tests fail (code review)**

`api/routers/stock.py` doesn't exist yet.

- [ ] **Step 3: Implement stock router**

Create `trader/api/routers/stock.py`:

```python
"""Stock detail API router.

GET /api/stock/{ticker} — full analysis for one ticker.
Triggers a background refresh if data is stale (>15 min).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

from cache import read_cache
from config import WATCHLIST_STALE_HOURS
from scoring.engine import compute_full_score

logger = logging.getLogger(__name__)
router = APIRouter()

_STALE_MINUTES = WATCHLIST_STALE_HOURS * 60


@router.get("/stock/{ticker}")
def get_stock(ticker: str, background_tasks: BackgroundTasks) -> dict:
    ticker = ticker.upper()
    data = read_cache(ticker)
    if data is None:
        # Not cached — trigger immediate fetch, return 404 (client should retry)
        background_tasks.add_task(_refresh, ticker)
        raise HTTPException(
            status_code=404,
            detail=f"{ticker} not in cache yet — refresh triggered, try again shortly",
        )

    # Trigger background refresh if stale
    fetched_at_str = data.get("fetched_at")
    if fetched_at_str:
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
            age_minutes = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 60
            if age_minutes > _STALE_MINUTES:
                background_tasks.add_task(_refresh, ticker)
        except Exception:
            pass

    scores = compute_full_score(data)
    fund = data.get("fundamentals", {})
    close = data.get("ohlcv", {}).get("close", [])

    return {
        "ticker": ticker,
        "company": fund.get("company_name", ticker),
        "price": round(close[-1], 2) if close else None,
        "technical_score": scores["technical"],
        "fundamental_score": scores["fundamental"],
        "sentiment_score": scores["sentiment"],
        "final_score": scores["final"],
        "verdict": scores["verdict"],
        "ohlcv": data.get("ohlcv", {}),
        "patterns": scores["patterns_detected"],
        "technical_drivers": scores["technical_drivers"],
        "fundamental_drivers": scores["fundamental_drivers"],
        "sentiment_drivers": scores["sentiment_drivers"],
        "fundamentals": {
            k: fund.get(k)
            for k in (
                "pe_ratio", "ev_ebitda", "revenue_growth_yoy",
                "gross_margin", "operating_margin", "debt_equity",
                "sector", "company_name",
            )
        },
        "fetched_at": data.get("fetched_at"),
    }


def _refresh(ticker: str) -> None:
    from scheduler import refresh_ticker_now
    refresh_ticker_now(ticker)
```

- [ ] **Step 4: Verify tests pass (code review)**

Confirm response shape matches all assertions. Confirm 404 when `read_cache` returns `None`.

- [ ] **Step 5: Commit**

```bash
git add trader/api/routers/stock.py trader/tests/test_api.py
git commit -m "feat: stock detail router GET /api/stock/{ticker}"
```

---

## Task 8: Screener Router + Railway Deployment

**Files:**
- Create: `trader/api/routers/screener.py`
- Modify: `trader/tests/test_api.py` (add screener tests)

- [ ] **Step 1: Write failing tests**

Append to `trader/tests/test_api.py`:

```python
def test_screener_returns_filtered_results():
    mock_cache = {
        "ohlcv": {"close": [150.0], "dates": ["2026-04-30"]},
        "fundamentals": {"company_name": "Apple Inc", "sector": "Technology", "missing_fields": []},
        "sentiment_items": [],
        "_override_scores": {"technical": 80, "fundamental": 75, "sentiment": 70},
    }
    # Patch sp500 list and read_cache
    with patch("api.routers.screener._load_sp500", return_value=["AAPL", "MSFT"]):
        with patch("cache.read_cache", return_value=mock_cache):
            response = client.get("/api/screener?min_score=60")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(r["final_score"] >= 60 for r in data if r["final_score"] is not None)


def test_screener_filters_by_verdict():
    mock_cache = {
        "ohlcv": {"close": [100.0], "dates": ["2026-04-30"]},
        "fundamentals": {"company_name": "Test", "missing_fields": []},
        "sentiment_items": [],
        "_override_scores": {"technical": 80, "fundamental": 80, "sentiment": 80},
    }
    with patch("api.routers.screener._load_sp500", return_value=["AAPL"]):
        with patch("cache.read_cache", return_value=mock_cache):
            response = client.get("/api/screener?verdict=Strong+BUY")
    assert response.status_code == 200
```

- [ ] **Step 2: Verify tests fail (code review)**

`api/routers/screener.py` doesn't exist yet.

- [ ] **Step 3: Implement screener router**

Create `trader/api/routers/screener.py`:

```python
"""Screener API router.

GET /api/screener — filter S&P 500 tickers by score/verdict/sector.
Only returns tickers that have a cached entry (no live fetches triggered).
"""

import csv
import logging
import os
from functools import lru_cache

from fastapi import APIRouter

from cache import read_cache
from config import SCREENER_UNIVERSE
from scoring.engine import compute_full_score

logger = logging.getLogger(__name__)
router = APIRouter()


@lru_cache(maxsize=1)
def _load_sp500() -> list[str]:
    """Load tickers from data/sp500.csv. Cached for process lifetime."""
    tickers = []
    try:
        with open(SCREENER_UNIVERSE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get("ticker") or row.get("Symbol") or ""
                if ticker:
                    tickers.append(ticker.upper())
    except Exception:
        logger.exception("Failed to load S&P 500 universe from %s", SCREENER_UNIVERSE)
    return tickers


@router.get("/screener")
def screener(
    min_score: int = 0,
    verdict: str = "",
    sector: str = "",
    limit: int = 100,
) -> list[dict]:
    results = []
    for ticker in _load_sp500():
        data = read_cache(ticker)
        if data is None:
            continue
        scores = compute_full_score(data)
        final = scores["final"]
        if final is None:
            continue
        if final < min_score:
            continue
        if verdict and scores["verdict"] != verdict:
            continue
        ticker_sector = data.get("fundamentals", {}).get("sector", "")
        if sector and ticker_sector != sector:
            continue

        close = data.get("ohlcv", {}).get("close", [])
        results.append(
            {
                "ticker": ticker,
                "company": data.get("fundamentals", {}).get("company_name", ticker),
                "sector": ticker_sector,
                "price": round(close[-1], 2) if close else None,
                "final_score": final,
                "verdict": scores["verdict"],
            }
        )
        if len(results) >= limit:
            break

    return sorted(results, key=lambda r: r["final_score"] or 0, reverse=True)
```

- [ ] **Step 4: Verify tests pass (code review)**

Confirm filtering logic, `_load_sp500` CSV parsing, and sort order.

- [ ] **Step 5: Commit**

```bash
git add trader/api/routers/screener.py trader/tests/test_api.py
git commit -m "feat: screener router GET /api/screener with score/verdict/sector filters"
```

- [ ] **Step 6: Verify full backend (code review)**

Read `api/main.py`, all routers, `cache.py`, `data/finbert.py`, `scheduler.py` together and confirm:
- All routers are included in `main.py`
- CORS is open (`allow_origins=["*"]`)
- Scheduler starts on lifespan startup and stops on shutdown
- `read_cache` / `write_cache` match the Supabase upsert pattern
- `classify_batch` handles 503 retry and empty input

- [ ] **Step 7: Deploy to Railway**

```bash
# Railway deployment (run from the trader/ directory)
# 1. Install Railway CLI: npm install -g @railway/cli  (or download from railway.app)
# 2. Login: railway login
# 3. Create project: railway new
# 4. Set env vars in Railway dashboard:
#    SUPABASE_URL, SUPABASE_KEY, HF_API_KEY
# 5. Deploy: railway up

# After deployment, confirm:
# curl https://your-app.railway.app/api/health
# Expected: {"status":"ok"}
```

- [ ] **Step 8: Final commit**

```bash
git add .
git commit -m "chore: backend complete — FastAPI + Supabase + HF API ready for Railway"
```
