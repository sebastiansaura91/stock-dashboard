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
