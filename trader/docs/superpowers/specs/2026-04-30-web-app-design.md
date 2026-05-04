# Stock Dashboard Web App — Design Spec

## Goal

Migrate the existing Streamlit-based stock analysis dashboard to a commercially viable web application: Next.js frontend hosted on Vercel, FastAPI backend hosted on Railway, Supabase as the database, and HuggingFace Inference API replacing the local FinBERT model. The result is a public URL anyone can visit — no local setup required.

## Architecture

```
Browser → Next.js (Vercel, free) → FastAPI (Railway, ~$0–3/mo) → Supabase (free)
                                                                 → HuggingFace Inference API (free)
                                                                 → yfinance / RSS feeds (free)
```

- **No authentication.** The app is public. Anyone with the URL can view it.
- **Next.js** serves the UI and calls the FastAPI backend via REST.
- **FastAPI** wraps the existing Python scoring engine. All scoring logic (technical, fundamental, sentiment, engine) is reused unchanged.
- **Supabase** replaces the local JSON file cache. Two tables: `tickers` (JSONB cache per ticker) and `watchlist` (list of tracked tickers).
- **HuggingFace Inference API** replaces the local FinBERT model. Same model (`ProsusAI/finbert`), called via HTTP. Free tier (~30k requests/month). Falls back gracefully to N/A if unavailable.
- **APScheduler** runs inside FastAPI (same as current `scheduler.py`) and refreshes all cached tickers every 15 minutes.

## What Gets Reused vs Changed

| Module | Status | Notes |
|--------|--------|-------|
| `scoring/technical.py` | ✅ Reused | No changes |
| `scoring/fundamental.py` | ✅ Reused | No changes |
| `scoring/sentiment_score.py` | ✅ Reused | No changes |
| `scoring/engine.py` | ✅ Reused | No changes |
| `data/fetcher.py` | ✅ Reused | No changes |
| `data/sentiment.py` | ✅ Reused | No changes |
| `cache.py` | 🔄 Replaced | Supabase client with same interface (`read_cache`, `write_cache`) |
| `data/finbert.py` | 🔄 Replaced | HTTP client to HF Inference API, same `classify_batch` interface |
| `scheduler.py` | 🔄 Adapted | Runs inside FastAPI on startup |
| `config.py` | 🔄 Extended | Add Supabase + HF API config; env-var driven |
| `pages/` | 🗑️ Dropped | Replaced by Next.js frontend |
| `app.py` | 🗑️ Dropped | Replaced by FastAPI `main.py` |
| `launcher.py`, `run.bat` | 🗑️ Dropped | No longer needed |

## Backend — FastAPI

### File structure

```
trader/
  api/
    main.py          # FastAPI app, scheduler startup, CORS
    routers/
      watchlist.py   # GET /api/watchlist, POST /api/watchlist, DELETE /api/watchlist/{ticker}
      stock.py       # GET /api/stock/{ticker}
      screener.py    # GET /api/screener
    db.py            # Supabase client (replaces cache.py)
    finbert_api.py   # HF Inference API client (replaces data/finbert.py)
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/watchlist` | Returns scores + verdicts for all watchlist tickers |
| `POST` | `/api/watchlist` | Body: `{"ticker": "AAPL"}` — adds ticker to watchlist |
| `DELETE` | `/api/watchlist/{ticker}` | Removes ticker from watchlist |
| `GET` | `/api/stock/{ticker}` | Full analysis: scores, drivers, patterns, OHLCV for chart |
| `GET` | `/api/screener` | Query params: `min_score`, `verdict`, `sector`, `limit` |

### Scheduler

APScheduler `BackgroundScheduler` starts on FastAPI `startup` event. Refreshes all watchlist tickers every 15 minutes. Same logic as current `scheduler.py`.

### Environment variables (Railway)

```
SUPABASE_URL=
SUPABASE_KEY=
HF_API_KEY=
HF_API_URL=https://api-inference.huggingface.co/models/ProsusAI/finbert
```

## Database — Supabase

### Tables

```sql
create table tickers (
  ticker      text primary key,
  data        jsonb not null,
  updated_at  timestamptz default now()
);

create table watchlist (
  ticker      text primary key,
  added_at    timestamptz default now()
);
```

`tickers.data` stores the same JSONB structure as the current local `.json` cache files — no change to the scoring engine's input/output contract.

## Sentiment — HuggingFace Inference API

`data/finbert.py` is replaced by `api/finbert_api.py` with the same public interface:

```python
def classify_batch(texts: list[str]) -> list[dict]:
    # POST to https://api-inference.huggingface.co/models/ProsusAI/finbert
    # Returns [{"label": "positive"|"negative"|"neutral", "score": float}]
    # On failure: returns [{"label": "neutral", "score": 0.0}] per item
```

Calls are batched (up to `FINBERT_BATCH_SIZE=16` per request). If the API is unavailable or the monthly limit is hit, all items return neutral with score 0.0 — the sentiment sub-score becomes N/A, and the engine renormalises the final score across the remaining components.

## Frontend — Next.js

### File structure

```
web/
  app/
    page.tsx                  # Redirects to /watchlist
    watchlist/
      page.tsx                # Watchlist page
    screener/
      page.tsx                # Screener page
    stock/
      [ticker]/
        page.tsx              # Stock detail page
  components/
    VerdictBadge.tsx          # Coloured pill: Strong BUY / BUY / HOLD / SELL / Strong SELL
    ScoreBar.tsx              # 0–100 progress bar with colour
    StockTable.tsx            # Sortable table used on watchlist + screener
    PriceChart.tsx            # 6-month candlestick chart (Lightweight Charts)
    PatternCard.tsx           # Chart pattern with name, explanation, direction badge
    DriverList.tsx            # Bullet list of score drivers
  lib/
    api.ts                    # All fetch calls to FastAPI
  styles/
    globals.css               # Tailwind base
```

### Page 1 — Watchlist (`/watchlist`)

- Search box to add a ticker (calls `POST /api/watchlist`)
- Sortable table: Ticker | Company | Price | Score | Verdict | Last Updated
- Each row links to `/stock/[ticker]`
- Verdict column uses `VerdictBadge` (green/amber/red)
- Remove button per row
- Data auto-refreshes every 15 minutes via `setInterval`

### Page 2 — Stock Detail (`/stock/[ticker]`)

Sections (top to bottom):

1. **Header** — ticker, company name, current price, large `VerdictBadge`
2. **Score cards** — three cards: Technical / Fundamental / Sentiment, each with a `ScoreBar` and sub-score number. Feed into a combined Final Score card.
3. **Price chart** — 6-month candlestick using TradingView Lightweight Charts (free, open-source). Volume bars below.
4. **Chart patterns** — one `PatternCard` per detected pattern showing:
   - Pattern name (e.g. "Double Bottom")
   - Plain-English meaning (e.g. "Two equal lows — typically signals a bullish reversal")
   - Reliability label (High / Medium)
   - Direction badge (bullish / bearish / neutral)
5. **Driver breakdowns** — three collapsible sections (Technical / Fundamental / Sentiment), each containing a `DriverList` of bullet points explaining the score
6. **Key ratios table** — P/E, EV/EBITDA, Revenue Growth, Gross Margin, Operating Margin, Debt/Equity with value + strong/neutral/weak label

### Page 3 — Screener (`/screener`)

- Filter bar: Min Score (slider), Verdict (dropdown), Sector (dropdown)
- Sortable results table (same `StockTable` component as watchlist)
- "Add to watchlist" button per row
- Results capped at 100 by default

### Styling

- Tailwind CSS
- Clean white background, dark text, minimal chrome
- Accent colour: indigo (`#6366f1`) for interactive elements
- Verdict colours: Strong BUY = green-700, BUY = green-500, HOLD = amber-500, SELL = red-500, Strong SELL = red-700
- No dark mode (out of scope)

## Deployment

### One-time setup

1. **Supabase** — create free project, run the two `CREATE TABLE` statements above
2. **Railway** — connect GitHub repo, point at `trader/` directory, set env vars, deploy
3. **Vercel** — connect GitHub repo, point at `web/` directory, set `NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app`, deploy

### Repo structure after migration

```
/
  trader/          # Python backend (FastAPI)
  web/             # Next.js frontend
  README.md
```

### CORS

FastAPI allows requests from the Vercel domain and `localhost:3000` for local development.

## Out of Scope

- User authentication / accounts
- Real-time WebSocket price streaming
- Dark mode
- Mobile-optimised layout (responsive but not mobile-first)
- Paid data sources
- Email alerts or notifications
