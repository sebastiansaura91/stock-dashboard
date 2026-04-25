# Wall Street Trader Technical Analysis Dashboard — Design Spec
**Date:** 2026-04-25

## Overview

A local web application (Python + Streamlit) that acts as a professional-grade stock analysis dashboard. It combines technical analysis (indicators + chart pattern recognition), fundamental key ratios, and free-source sentiment data into a single weighted score per stock, producing a transparent BUY / HOLD / SELL verdict with full reasoning breakdown.

---

## Goals

- Give a clear, explainable trade signal for any stock with supporting evidence
- Cover three analysis dimensions: technical, fundamental, sentiment
- Surface new opportunities via a screener over the S&P 500 universe
- Run entirely locally using free APIs and data sources — no paid subscriptions
- Never block the UI — all data fetching happens in a background scheduler

---

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Frontend + backend | Python + Streamlit | Single language, fastest iteration, great finance library support |
| Charts | Plotly (via `st.plotly_chart`) | Interactive candlesticks, pattern annotations |
| Technical indicators | `pandas-ta` | 100+ indicators, pure Python, no TA-Lib C dependency |
| Price + fundamentals | `yfinance` | Free, no auth, OHLCV + financials + ratios |
| Sentiment NLP | `transformers` + FinBERT (`ProsusAI/finbert`) | Finance-tuned model, runs locally on CPU, no API cost |
| Background scheduler | `APScheduler` (BackgroundScheduler) | Runs in a daemon thread, guarded against Streamlit reruns |
| Cache | Disk JSON per ticker in `cache/` | Survives restarts, no database dependency |
| File locking | `portalocker` | Safe concurrent read/write between scheduler and UI |
| Logging | Python `logging` to `logs/trader.log` | Scheduler job failures, fetch errors, rate limit events |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit App                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  Watchlist  │  │ Stock Detail │  │  Screener │  │
│  │  Dashboard  │  │    Page      │  │   Page    │  │
│  └─────────────┘  └──────────────┘  └───────────┘  │
└────────────────────────┬────────────────────────────┘
                         │ reads cache (portalocker shared lock)
              ┌──────────▼──────────┐
              │   Cache Layer       │
              │  cache/<TICKER>.json│
              │  (portalocker write)│
              └──────────┬──────────┘
                         │ written by scheduler daemon thread
              ┌──────────▼──────────┐
              │   APScheduler       │
              │  (singleton guard)  │
              └──────────┬──────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Technical   │ │ Fundamental  │ │  Sentiment   │
│  yfinance    │ │  yfinance    │ │  RSS feeds   │
│  pandas-ta   │ │  financials  │ │  StockTwits  │
│  (OHLCV)     │ │  ratios      │ │  Reddit RSS  │
└──────────────┘ └──────────────┘ └──────────────┘
```

**Data flow:** APScheduler daemon thread calls fetcher + sentiment modules on schedule → writes to `cache/<TICKER>.json` (exclusive file lock) → Streamlit pages read from cache (shared file lock) → scoring engine computes scores at read time for display. No live API calls during UI rendering.

---

## Project Structure

```
trader/
├── app.py                  # Streamlit entry point, scheduler singleton init, page routing
├── scheduler.py            # APScheduler setup, job definitions, singleton guard
├── config.py               # Watchlist tickers, weights, universe path, intervals
├── cache/                  # Per-ticker JSON cache files (gitignored)
├── logs/                   # Rotating log file (gitignored)
├── data/
│   ├── fetcher.py          # yfinance OHLCV + fundamentals fetch
│   ├── sentiment.py        # RSS, StockTwits, Reddit scraping + raw text
│   ├── finbert.py          # FinBERT singleton loader + batch inference
│   └── sp500.csv           # S&P 500 ticker list — columns: ticker, name, sector, market_cap_category
├── scoring/
│   ├── technical.py        # Indicators + chart pattern detection + scoring
│   ├── fundamental.py      # Ratio scoring
│   ├── sentiment_score.py  # FinBERT NLP pipeline → sentiment score
│   └── engine.py           # Weighted combiner → final score + verdict
├── pages/
│   ├── watchlist.py        # Watchlist dashboard page
│   ├── detail.py           # Stock detail page
│   └── screener.py         # Screener page
└── requirements.txt
```

---

## APScheduler Singleton (Critical Implementation Detail)

Streamlit reruns `app.py` on every user interaction. The scheduler must start exactly once per process. Guard pattern in `app.py`:

```python
import streamlit as st
from scheduler import start_scheduler

if "scheduler_started" not in st.session_state:
    start_scheduler()
    st.session_state["scheduler_started"] = True
```

`start_scheduler()` in `scheduler.py` uses a module-level flag AND checks `APScheduler`'s running state before calling `.start()`. The scheduler runs as a `BackgroundScheduler` daemon thread — it will stop automatically when the Streamlit process exits.

---

## Cache Schema

Each ticker has one file: `cache/<TICKER>.json`. Schema:

```json
{
  "ticker": "AAPL",
  "updated_at": "2026-04-25T14:30:00Z",
  "fetch_error": false,
  "fetch_error_at": null,
  "sentiment_stale": false,
  "ohlcv": {
    "dates": ["2026-01-02", "..."],
    "open": [180.1, "..."],
    "high": [182.5, "..."],
    "low": [179.0, "..."],
    "close": [181.2, "..."],
    "volume": [75000000, "..."]
  },
  "fundamentals": {
    "pe_ratio": 28.4,
    "ev_ebitda": 21.1,
    "revenue_growth_yoy": 0.08,
    "gross_margin": 0.44,
    "operating_margin": 0.30,
    "debt_equity": 1.7,
    "sector": "Technology",
    "missing_fields": ["ev_ebitda"]
  },
  "sentiment_items": [
    {
      "source": "google_news",
      "headline": "Apple beats earnings expectations",
      "published_at": "2026-04-24T18:00:00Z",
      "label": "positive",
      "score": 0.91
    }
  ],
  "scores": {
    "technical": 72,
    "fundamental": 65,
    "sentiment": 58,
    "final": 67,
    "verdict": "BUY",
    "patterns_detected": [
      {
        "name": "Bull Flag",
        "detected_at": "2026-04-23",
        "meaning": "Short consolidation after a strong uptrend — typically signals continuation higher.",
        "reliability": "Medium",
        "direction": "bullish"
      }
    ],
    "technical_drivers": ["RSI neutral (54)", "MACD bullish crossover", "Price above EMA 20/50/200"],
    "fundamental_drivers": ["P/E below sector median", "Strong gross margin"],
    "sentiment_drivers": ["7 bullish / 2 bearish / 3 neutral items in last 24h"]
  }
}
```

**Missing values:** Any `null` fundamental field is excluded from scoring. If more than 3 of 6 ratios are null, fundamental score is marked `null` and the final score is computed from the remaining two sub-scores proportionally.

**File write strategy:** Scheduler writes to `cache/<TICKER>.json.tmp` first, then renames to `cache/<TICKER>.json` (atomic on POSIX; best-effort on Windows). Reads use `portalocker` shared lock to avoid reading mid-write.

---

## Scoring Engine

All scores are integers 0–100. Final score is computed as `floor(weighted_average)`. Verdict uses `>=` comparisons on the floored value.

### Default Weights (user-adjustable via UI sliders)
```python
DEFAULT_WEIGHTS = {"technical": 0.40, "fundamental": 0.35, "sentiment": 0.25}
```

### Technical Score

Each indicator produces a signal in `{-1, 0, +1}` (bearish, neutral, bullish). Signals are converted to a 0–100 component score. Final technical score = weighted average of component scores, mapped to 0–100.

**Indicator signals and component weights:**

| Indicator | Bullish condition (+1) | Bearish condition (-1) | Weight |
|-----------|----------------------|----------------------|--------|
| EMA 20/50 | Price > EMA20 > EMA50 | Price < EMA20 < EMA50 | 10% |
| EMA 50/200 | EMA50 > EMA200 (golden cross) | EMA50 < EMA200 (death cross) | 10% |
| ADX | ADX > 25 and +DI > -DI | ADX > 25 and -DI > +DI | 8% |
| RSI | RSI < 40 (room to run) | RSI > 65 (overbought) | 12% |
| MACD | MACD line > signal line | MACD line < signal line | 10% |
| Stochastic | %K < 30 and %K crossing up %D | %K > 70 and %K crossing down %D | 8% |
| Bollinger | Price near lower band | Price near upper band | 7% |
| ATR | Low ATR (stable trend) | High ATR (high volatility) | 5% |
| OBV | OBV trending up | OBV trending down | 10% |
| Volume | Volume > 1.5× 20-day avg on up day | Volume > 1.5× 20-day avg on down day | 5% |
| Patterns | Bullish pattern detected | Bearish pattern detected | 15% |

Signal-to-score: +1 → 100, 0 → 50, -1 → 0. Final technical score = sum of (component_score × weight).

### Chart Pattern Detection

Detection uses `scipy.signal.find_peaks` on closing prices. Each pattern has its own lookback window (30–90 days as specified below). Tolerance = 2% of price range.

| Pattern | Algorithm | Lookback | Bullish/Bearish |
|---------|-----------|----------|-----------------|
| Head & Shoulders | 3 peaks: left shoulder ≈ right shoulder < head | 60 days | Bearish |
| Inverse H&S | 3 troughs: left ≈ right < head (inverted) | 60 days | Bullish |
| Double Top | 2 peaks within 2% of each other, separated ≥ 10 days | 60 days | Bearish |
| Double Bottom | 2 troughs within 2% of each other, separated ≥ 10 days | 60 days | Bullish |
| Ascending Triangle | Rising troughs, flat resistance peaks | 40 days | Bullish |
| Descending Triangle | Falling peaks, flat support troughs | 40 days | Bearish |
| Symmetrical Triangle | Converging peaks and troughs | 40 days | Neutral (+0) |
| Bull Flag | Strong uptrend followed by tight downward channel ≤ 10 days | 30 days | Bullish |
| Bear Flag | Strong downtrend followed by tight upward channel ≤ 10 days | 30 days | Bearish |
| Cup & Handle | U-shaped base ≥ 30 days, then small pullback | 90 days | Bullish |

At most the **most recently detected pattern** counts toward the technical score. If multiple patterns are detected, all are shown in the UI but only the most recent affects the score.

### Fundamental Score

Sector medians are computed from the watchlist + screener universe tickers themselves (using `yfinance` data). On first run with insufficient data, absolute fallback thresholds are used:

| Ratio | Bullish (score 100) | Bearish (score 0) | Fallback bullish | Fallback bearish | Weight |
|-------|--------------------|--------------------|-----------------|-----------------|--------|
| P/E ratio | < sector median × 0.8 | > sector median × 1.5 | < 18 | > 35 | 20% |
| EV/EBITDA | < sector median × 0.8 | > sector median × 1.5 | < 12 | > 25 | 20% |
| Revenue growth YoY | > 10% | < 0% | > 10% | < 0% | 20% |
| Gross margin | > sector median | < sector median × 0.7 | > 0.40 | < 0.15 | 15% |
| Operating margin | > 15% | < 5% | > 0.15 | < 0.05 | 15% |
| Debt/Equity | < 1.0 | > 3.0 | < 1.0 | > 3.0 | 10% |

Each ratio is scored 0–100 on a linear scale between its bearish and bullish thresholds. Missing ratios are excluded; weight redistributed proportionally among available ratios. Fundamental score = weighted average of available ratio scores.

### Sentiment Score

**Data sources:**

| Source | URL pattern | Fields used |
|--------|-------------|-------------|
| Google News RSS | `https://news.google.com/rss/search?q={TICKER}+stock&hl=en-US&gl=US&ceid=US:en` | `title` |
| StockTwits public API | `https://api.stocktwits.com/api/2/streams/symbol/{TICKER}.json` | `body` of messages |
| Reddit r/stocks RSS | `https://www.reddit.com/r/stocks/search.rss?q={TICKER}&sort=new` | `title` |
| Reddit r/investing RSS | `https://www.reddit.com/r/investing/search.rss?q={TICKER}&sort=new` | `title` |
| Finviz news | `https://finviz.com/quote.ashx?t={TICKER}` — scrape news table | headline text |

Finviz scrape uses a rotating set of common browser User-Agent strings and a 2-second delay between requests. If Finviz returns 403 or 429, it is skipped for that cycle (logged, not fatal).

**Rate limit handling:** All sources use exponential backoff (1s, 2s, 4s) with max 3 retries. On failure, the previous cache sentiment items are preserved and a `sentiment_stale: true` flag is set in the cache file.

**FinBERT loading:** The model is loaded once at scheduler startup into a module-level singleton in `data/finbert.py`. It runs on CPU. Estimated RAM: ~500 MB. Inference is batched (batch size 16) to avoid repeated model calls. Load time ~15 seconds on first run.

**Scoring:**
- Each item is classified: `positive` (+1), `negative` (-1), `neutral` (0)
- Items are filtered to those published within the last 48 hours
- Recency weight: exponential decay with 12-hour half-life (`weight = exp(-age_hours / 12)`)
- Items with no parseable timestamp get weight = 0.1 (included but heavily discounted)
- Sentiment score = weighted mean of item scores, where each item score is: `positive → 1.0`, `neutral → 0.5`, `negative → 0.0`. Formula: `sum(label_score_i × weight_i) / sum(weight_i) × 100`. This normalises naturally to 0–100 regardless of item count.
- If fewer than 3 items are available, sentiment score is marked `null` and excluded from final scoring

### Final Verdict

Final score = `floor(tech × w_tech + fund × w_fund + sent × w_sent)` where null sub-scores are excluded and remaining weights are renormalized to sum to 1.0.

| Final Score | Signal |
|-------------|--------|
| >= 75 | Strong BUY |
| >= 60 | BUY |
| >= 45 | HOLD |
| >= 30 | SELL |
| < 30 | Strong SELL |

---

## UI Pages

### 1. Watchlist Dashboard
- Table: Ticker, Price, % Change, Final Score, Tech / Fund / Sent sub-scores, Signal badge (color-coded), Last Updated
- Missing/null sub-scores shown as `—`
- Click any row → navigates to Stock Detail page
- "Refresh All" button enqueues an immediate scheduler job for all watchlist tickers (non-blocking — UI returns instantly, data updates when jobs complete)
- Last scheduled refresh timestamp shown at top

### 2. Stock Detail Page
- Candlestick chart (Plotly, interactive) with detected patterns annotated as vertical lines + labels
- Three score panels side by side (Technical / Fundamental / Sentiment) — each shows sub-score, key drivers list, traffic-light indicator
- Pattern panel — all detected patterns in the last 90 days with: name, detection date, plain-English meaning, reliability rating, directional label
- Fundamental table — ratios vs. sector median, green/red color coding, `—` for missing
- Sentiment feed — up to 20 most recent items, each with source, headline, and Bullish / Bearish / Neutral badge
- Final verdict banner — large BUY/HOLD/SELL badge, score, one-sentence reasoning summary
- Weight sliders — adjusting sliders recomputes final score on-the-fly from cached sub-scores (no API call). Slider values are NOT persisted — they reset to `DEFAULT_WEIGHTS` on page reload
- Stale data warning shown if `updated_at` is > 2 hours ago

### 3. Screener Page
- Filter controls: minimum final score (slider), signal type (multiselect), sector (multiselect), market cap category (Small / Mid / Large — from `sp500.csv`)
- Universe: all tickers in `data/sp500.csv`
- Results table sorted by Final Score descending; tickers with null final score shown at bottom
- Scores read from cache — pre-computed by background scheduler
- Stale threshold for screener: 4 hours (different from watchlist 2 hours, since screener refreshes on a slower cadence)
- Last-refreshed timestamp shown; "Refresh Watchlist" button does NOT trigger screener refresh (too slow)

---

## Background Scheduler

**Refresh cadence:**
- Watchlist tickers: every 15 minutes
- Screener universe (S&P 500 minus watchlist): every 4 hours, staggered in batches of 50 tickers per sub-job to avoid hammering APIs

**Per-job behavior:**
1. Fetch OHLCV + fundamentals via `yfinance` (single ticker)
2. Fetch sentiment items from all sources (with retry + backoff)
3. Run FinBERT batch inference on new items not already scored
4. Compute all sub-scores and final score
5. Write to `cache/<TICKER>.json.tmp` then rename to `cache/<TICKER>.json`
6. Log success or failure to `logs/trader.log`

**Failure handling:**
- If fetch fails: preserve existing cache, set `fetch_error: true` and `fetch_error_at` timestamp
- If FinBERT fails: preserve existing sentiment scores, log error
- Scheduler job failures are caught and logged — never propagate to crash the Streamlit process

**Startup behavior:**
- On first run (empty cache), watchlist tickers are fetched immediately (blocking, before UI renders)
- Screener universe deferred to first scheduled job

---

## `data/sp500.csv` Schema

Sourced from Wikipedia S&P 500 list (can be refreshed manually). Columns:

```
ticker,name,sector,market_cap_category
AAPL,Apple Inc.,Technology,Large
MSFT,Microsoft Corporation,Technology,Large
...
```

`market_cap_category` values: `Large` (> $10B), `Mid` ($2B–$10B), `Small` (< $2B).

---

## Configuration (`config.py`)

```python
WATCHLIST = ["AAPL", "MSFT", "NVDA"]
SCREENER_UNIVERSE = "data/sp500.csv"
WATCHLIST_REFRESH_MINUTES = 15
SCREENER_REFRESH_HOURS = 4
SCREENER_BATCH_SIZE = 50
DEFAULT_WEIGHTS = {"technical": 0.40, "fundamental": 0.35, "sentiment": 0.25}
CACHE_DIR = "cache/"
LOG_FILE = "logs/trader.log"
SENTIMENT_LOOKBACK_HOURS = 48
SENTIMENT_HALF_LIFE_HOURS = 12
WATCHLIST_STALE_HOURS = 2
SCREENER_STALE_HOURS = 4
FINBERT_BATCH_SIZE = 16
```

---

## Error Handling & Observability

- All scheduler jobs wrapped in `try/except`, errors logged to `logs/trader.log` with ticker and timestamp
- UI shows inline warnings for: stale cache, missing sub-scores, fetch errors
- FinBERT load failure at startup → sentiment scoring disabled for session, warning shown in UI sidebar
- Log rotation: 5 MB max, 3 backup files (via `RotatingFileHandler`)

---

## `requirements.txt`

```
streamlit>=1.35.0
yfinance>=0.2.40
pandas-ta>=0.3.14b
plotly>=5.22.0
APScheduler>=3.10.0,<4.0      # v4 has breaking API changes for BackgroundScheduler
transformers>=4.40.0
torch>=2.2.0                   # CPU-only; FinBERT does not require GPU
portalocker>=2.8.0
feedparser>=6.0.11
requests>=2.31.0
beautifulsoup4>=4.12.0
scipy>=1.13.0
pandas>=2.2.0
```

## Running the App

```bash
pip install -r requirements.txt
streamlit run app.py
```

App opens at `http://localhost:8501`. On first run, watchlist data is fetched synchronously before the UI renders (~10–30 seconds). FinBERT model downloads on first run (~400 MB, cached by HuggingFace locally).

---

## Out of Scope

- Options, crypto, forex, commodities
- Paid API integrations
- User authentication
- Cloud hosting / deployment
- Backtesting engine
- Automated trade execution
- Per-stock persistent weight overrides (sliders reset on page reload)
