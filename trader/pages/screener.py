"""Screener page — bulk S&P 500 scanner ranked by final score."""

import csv
import logging
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from cache import read_cache
from config import SCREENER_BATCH_SIZE, SCREENER_STALE_HOURS, SCREENER_UNIVERSE
from scheduler import refresh_ticker_now
from scoring.engine import compute_full_score

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level helpers (importable by tests)
# ---------------------------------------------------------------------------


def _is_stale(cache_data: dict) -> bool:
    """Return True if *cache_data* is older than SCREENER_STALE_HOURS."""
    fetched_at = cache_data.get("fetched_at")
    if not fetched_at:
        return True
    try:
        dt = datetime.fromisoformat(fetched_at)
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return age_hours > SCREENER_STALE_HOURS
    except Exception:
        return True


def _load_universe() -> list[str]:
    """Load ticker list from SCREENER_UNIVERSE CSV."""
    try:
        with open(SCREENER_UNIVERSE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [row["ticker"] for row in reader]
    except Exception:
        return []


def _apply_filters(
    results: list[dict],
    min_score: int,
    verdict_filter: list[str],
    max_results: int,
) -> list[dict]:
    """Filter and sort results list. Each result is a dict with 'final', 'verdict', etc."""
    filtered = [
        r for r in results
        if r.get("final") is not None
        and r["final"] >= min_score
        and r["verdict"] in verdict_filter
    ]
    sorted_results = sorted(filtered, key=lambda r: r["final"], reverse=True)
    return sorted_results[:max_results]


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the S&P 500 Screener page."""
    st.title("🔍 S&P 500 Screener")

    # ------------------------------------------------------------------
    # Sidebar filter controls
    # ------------------------------------------------------------------
    min_score = st.sidebar.slider("Min Final Score", 0, 100, 50)
    verdict_filter = st.sidebar.multiselect(
        "Verdict Filter",
        options=["Strong BUY", "BUY", "HOLD", "SELL", "Strong SELL"],
        default=["Strong BUY", "BUY"],
    )
    max_results = st.sidebar.number_input(
        "Max Results", min_value=1, max_value=200, value=50, step=10
    )

    # ------------------------------------------------------------------
    # Scan button
    # ------------------------------------------------------------------
    if st.button("🚀 Run Screener"):
        universe = _load_universe()

        if not universe:
            st.error("Could not load ticker universe. Check that data/sp500.csv exists.")
        else:
            batch = universe[:SCREENER_BATCH_SIZE]
            total = len(batch)
            st.info(f"Scanning first {SCREENER_BATCH_SIZE} tickers...")

            progress_bar = st.progress(0)
            raw_results = []

            for i, ticker in enumerate(batch):
                cache_data = read_cache(ticker)

                # Refresh if missing or stale
                if cache_data is None or _is_stale(cache_data):
                    refresh_ticker_now(ticker)
                    cache_data = read_cache(ticker)

                if cache_data is None:
                    progress_bar.progress(int((i + 1) / total * 100))
                    continue

                try:
                    scores = compute_full_score(cache_data)
                except Exception as exc:
                    logger.warning("compute_full_score failed for %s: %s", ticker, exc)
                    progress_bar.progress(int((i + 1) / total * 100))
                    continue

                if scores["final"] is not None:
                    raw_results.append(
                        {
                            "ticker": ticker,
                            "final": scores["final"],
                            "verdict": scores["verdict"],
                            "technical": scores["technical"],
                            "fundamental": scores["fundamental"],
                            "sentiment": scores["sentiment"],
                        }
                    )

                progress_bar.progress(int((i + 1) / total * 100))

            # Apply filters, sort, and limit
            filtered = _apply_filters(raw_results, min_score, verdict_filter, int(max_results))
            st.session_state["screener_results"] = filtered

    # ------------------------------------------------------------------
    # Results display
    # ------------------------------------------------------------------
    results = st.session_state.get("screener_results")
    if results is not None:
        st.success(f"Found {len(results)} matching tickers")

        rows = []
        for r in results:
            rows.append(
                {
                    "Ticker": r["ticker"],
                    "Technical": r["technical"] if r["technical"] is not None else "N/A",
                    "Fundamental": r["fundamental"] if r["fundamental"] is not None else "N/A",
                    "Sentiment": r["sentiment"] if r["sentiment"] is not None else "N/A",
                    "Final": r["final"] if r["final"] is not None else "N/A",
                    "Verdict": r["verdict"],
                }
            )

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        for r in results:
            ticker = r["ticker"]
            if st.button(f"View Detail: {ticker}", key=f"detail_{ticker}"):
                st.session_state["selected_ticker"] = ticker
                st.session_state["page"] = "detail"
                st.rerun()
