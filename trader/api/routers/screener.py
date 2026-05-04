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
