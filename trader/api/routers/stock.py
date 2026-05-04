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
            # Ensure timezone-aware for comparison (treat naive timestamps as UTC)
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)
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
