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
| Sentiment NLP | `transformers` + FinBERT | Finance-tuned model, runs locally, no API cost |
| Background scheduler | `APScheduler` | Runs inside Streamlit process, no second process needed |
| Cache | Disk (JSON per ticker in `cache/`) | Survives restarts, no database dependency |

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
                         │
              ┌──────────▼──────────┐
              │   Scoring Engine    │
              │  Tech | Fund | Sent │
              │   → Weighted Score  │
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
                         │
              ┌──────────▼──────────┐
              │   Cache Layer       │
              │  (disk JSON/pickle) │
              │  APScheduler 15min  │
              └─────────────────────┘
```

**Data flow:** APScheduler calls fetcher + sentiment modules every 15 minutes → writes raw data to `cache/<TICKER>.json` → scoring engine reads cache and computes scores → Streamlit pages read scores and render. No live API calls happen during UI rendering.

---

## Project Structure

```
trader/
├── app.py                  # Streamlit entry point, page routing
├── scheduler.py            # APScheduler setup, background refresh loop
├── config.py               # Watchlist tickers, score weights, universe path
├── cache/                  # Per-ticker JSON cache files
├── data/
│   ├── fetcher.py          # yfinance OHLCV + fundamentals fetch
│   ├── sentiment.py        # RSS, StockTwits, Reddit scraping + raw text
│   └── sp500.csv           # S&P 500 ticker list (static, free from Wikipedia)
├── scoring/
│   ├── technical.py        # Indicators + chart pattern detection + scoring
│   ├── fundamental.py      # Ratio scoring vs. sector averages
│   ├── sentiment_score.py  # FinBERT NLP pipeline → sentiment score
│   └── engine.py           # Weighted combiner → final score + verdict
├── pages/
│   ├── watchlist.py        # Watchlist dashboard page
│   ├── detail.py           # Stock detail page
│   └── screener.py         # Screener page
└── requirements.txt
```

---

## Scoring Engine

All scores are 0–100. Final score is a weighted average of three sub-scores.

### Default Weights (user-adjustable via UI sliders)
- Technical: 40%
- Fundamental: 35%
- Sentiment: 25%

### Technical Score

Computed from:

**Trend**
- EMA 20/50/200 crossover states (price above/below each, crossover events)
- ADX strength (> 25 = strong trend)

**Momentum**
- RSI (< 30 oversold = bullish, > 70 overbought = bearish)
- MACD line vs. signal line
- Stochastic %K/%D

**Volatility**
- Bollinger Band position (price relative to upper/lower bands)
- ATR normalized to price

**Volume**
- OBV trend direction
- Current volume vs. 20-day average

**Chart Pattern Detection**
Detected algorithmically using pivot points on OHLCV data:

| Pattern | Signal | Reliability |
|---------|--------|-------------|
| Head & Shoulders | Bearish reversal | High |
| Inverse Head & Shoulders | Bullish reversal | High |
| Double Top | Bearish reversal | High |
| Double Bottom | Bullish reversal | High |
| Ascending Triangle | Bullish continuation | Medium |
| Descending Triangle | Bearish continuation | Medium |
| Symmetrical Triangle | Neutral / breakout pending | Medium |
| Bull Flag | Bullish continuation | Medium |
| Bear Flag | Bearish continuation | Medium |
| Cup & Handle | Bullish breakout setup | Medium |

Each detected pattern is shown on the candlestick chart with an annotation, and listed in a pattern panel with: name, detection date, plain-English meaning, typical reliability, and directional impact on score.

### Fundamental Score

Key ratios pulled from `yfinance`, scored vs. sector median:

- P/E ratio (sector-relative)
- EV/EBITDA
- Revenue growth YoY
- Gross margin
- Operating margin
- Debt/Equity ratio

Each ratio scored 0–100 based on percentile within sector. Fundamental score = average of ratio scores.

### Sentiment Score

**Data sources (all free):**
- Google News RSS per ticker
- StockTwits public stream (no auth required)
- Reddit r/stocks + r/investing via RSS
- Finviz news page scrape

**Processing:**
- FinBERT (`ProsusAI/finbert`) classifies each item as Positive / Negative / Neutral
- Score = weighted average of classifications (recent items weighted higher)
- Volume of mentions factored in (more coverage = higher confidence)

### Final Verdict

| Final Score | Signal |
|-------------|--------|
| 75–100 | Strong BUY |
| 60–74 | BUY |
| 45–59 | HOLD |
| 30–44 | SELL |
| 0–29 | Strong SELL |

---

## UI Pages

### 1. Watchlist Dashboard
- Table: Ticker, Price, % Change, Final Score, Tech / Fund / Sent sub-scores, Signal badge (color-coded), Last Updated
- Click any row → navigates to Stock Detail page
- "Refresh All" button triggers manual cache refresh
- Last scheduled refresh timestamp shown

### 2. Stock Detail Page
- **Candlestick chart** (Plotly, interactive) with detected patterns annotated on the chart
- **Three score panels** (Technical / Fundamental / Sentiment) — each shows sub-score, key driving factors, traffic-light indicator
- **Pattern panel** — all detected patterns with name, date, plain-English meaning, reliability, and directional label
- **Fundamental table** — ratios vs. sector median, green/red color coding
- **Sentiment feed** — recent headlines and StockTwits posts with Bullish / Bearish / Neutral label per item
- **Final verdict banner** — prominent BUY/HOLD/SELL badge with weighted score and one-sentence reasoning summary
- **Weight sliders** — adjust tech/fund/sentiment weights, verdict updates live

### 3. Screener Page
- Filter controls: minimum final score, signal type, sector, market cap range
- Universe: S&P 500 tickers (loaded from `data/sp500.csv`)
- Results table sorted by Final Score descending
- Scores pre-computed by background scheduler — no blocking on page load
- Last-refreshed timestamp shown

---

## Data Sources (all free)

| Data | Source | Method |
|------|--------|--------|
| OHLCV price history | Yahoo Finance | `yfinance` |
| Fundamentals + ratios | Yahoo Finance | `yfinance` |
| News headlines | Google News RSS | `feedparser` |
| Social sentiment | StockTwits public API | HTTP GET, no auth |
| Social sentiment | Reddit r/stocks RSS | `feedparser` |
| News sentiment | Finviz news page | `requests` + `BeautifulSoup` |
| S&P 500 universe | Wikipedia table | Static CSV (updated manually) |

---

## Background Scheduler

- Runs inside the Streamlit process using `APScheduler`
- Refresh interval: 15 minutes (configurable in `config.py`)
- On each tick: fetches all watchlist tickers + screener universe, writes to `cache/`
- Cache format: one JSON file per ticker with sections for OHLCV, fundamentals, sentiment items, computed scores, and timestamp
- Stale cache threshold: if a ticker's cache is > 2 hours old and scheduler failed, show a warning in UI

---

## Configuration (`config.py`)

```python
WATCHLIST = ["AAPL", "MSFT", "NVDA"]          # user-defined tickers
SCREENER_UNIVERSE = "data/sp500.csv"           # path to ticker universe
REFRESH_INTERVAL_MINUTES = 15
DEFAULT_WEIGHTS = {"technical": 0.40, "fundamental": 0.35, "sentiment": 0.25}
CACHE_DIR = "cache/"
```

---

## Running the App

```bash
pip install -r requirements.txt
streamlit run app.py
```

App opens at `http://localhost:8501`. Scheduler starts automatically on first run.

---

## Out of Scope

- Options, crypto, forex, commodities
- Paid API integrations
- User authentication
- Cloud hosting / deployment
- Backtesting engine
- Automated trade execution
