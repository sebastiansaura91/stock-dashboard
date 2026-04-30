"""Watchlist page — default landing page showing a live summary table."""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from cache import read_cache
from config import WATCHLIST, WATCHLIST_STALE_HOURS
from scheduler import refresh_ticker_now
from scoring.engine import compute_full_score


# ---------------------------------------------------------------------------
# Module-level helpers (importable by tests)
# ---------------------------------------------------------------------------

def _is_stale(cache_data: dict) -> bool:
    """Return True if *cache_data* is older than WATCHLIST_STALE_HOURS."""
    fetched_at = cache_data.get("fetched_at")
    if not fetched_at:
        return True
    try:
        dt = datetime.fromisoformat(fetched_at)
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return age_hours > WATCHLIST_STALE_HOURS
    except Exception:
        return True


def colour_verdict(val: str) -> str:
    """Return a CSS background-color style string for a verdict value."""
    if val in ("Strong BUY", "BUY"):
        return "background-color: #d4edda"
    if val in ("Strong SELL", "SELL"):
        return "background-color: #f8d7da"
    if val == "HOLD":
        return "background-color: #fff3cd"
    return ""


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------

def render() -> None:
    """Render the Watchlist page."""
    st.title("📋 Watchlist")

    # Initialise watchlist in session state from config on first load
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = list(WATCHLIST)

    # ------------------------------------------------------------------
    # Add / Remove controls
    # ------------------------------------------------------------------
    col_add, col_remove = st.columns([1, 2])

    with col_add:
        new_ticker = st.text_input("Add ticker", key="add_ticker_input")
        if st.button("Add"):
            ticker_upper = new_ticker.strip().upper()
            if ticker_upper and ticker_upper not in st.session_state["watchlist"]:
                st.session_state["watchlist"].append(ticker_upper)

    with col_remove:
        to_remove = st.multiselect(
            "Remove",
            options=st.session_state["watchlist"],
        )
        if st.button("Remove"):
            st.session_state["watchlist"] = [
                t for t in st.session_state["watchlist"] if t not in to_remove
            ]

    # ------------------------------------------------------------------
    # Refresh All button
    # ------------------------------------------------------------------
    if st.button("🔄 Refresh All"):
        for ticker in st.session_state["watchlist"]:
            refresh_ticker_now(ticker)
        st.rerun()

    # ------------------------------------------------------------------
    # Build score table
    # ------------------------------------------------------------------
    rows = []
    for ticker in st.session_state["watchlist"]:
        cache_data = read_cache(ticker)

        # Refresh if missing or stale
        if cache_data is None or _is_stale(cache_data):
            refresh_ticker_now(ticker)
            cache_data = read_cache(ticker)

        if cache_data is None:
            st.warning(f"{ticker}: data unavailable — could not fetch from source.")
            rows.append(
                {
                    "Ticker": ticker,
                    "Technical": "N/A",
                    "Fundamental": "N/A",
                    "Sentiment": "N/A",
                    "Final": "N/A",
                    "Verdict": "N/A",
                }
            )
            continue

        try:
            scores = compute_full_score(cache_data)
        except Exception as exc:
            st.warning(f"{ticker}: scoring failed — {exc}")
            rows.append({
                "Ticker": ticker, "Technical": "N/A", "Fundamental": "N/A",
                "Sentiment": "N/A", "Final": "N/A", "Verdict": "N/A",
            })
            continue
        rows.append(
            {
                "Ticker": ticker,
                "Technical": scores["technical"] if scores["technical"] is not None else "N/A",
                "Fundamental": scores["fundamental"] if scores["fundamental"] is not None else "N/A",
                "Sentiment": scores["sentiment"] if scores["sentiment"] is not None else "N/A",
                "Final": scores["final"] if scores["final"] is not None else "N/A",
                "Verdict": scores["verdict"],
            }
        )

    if rows:
        df = pd.DataFrame(rows)
        styled = df.style.map(colour_verdict, subset=["Verdict"])
        st.dataframe(styled, use_container_width=True)
