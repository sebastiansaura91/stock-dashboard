"""Stock Detail page — deep-dive view for a single ticker."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cache import read_cache
from pages.watchlist import _is_stale
from scheduler import refresh_ticker_now
from scoring.engine import compute_full_score


# ---------------------------------------------------------------------------
# Module-level helpers (importable by tests)
# ---------------------------------------------------------------------------

_FUNDAMENTAL_KEYS = [
    "pe_ratio",
    "ev_ebitda",
    "revenue_growth_yoy",
    "gross_margin",
    "operating_margin",
    "debt_equity",
]


def _build_fundamentals_rows(fundamentals: dict) -> list:
    """Return a list of {"Metric": str, "Value": str} dicts for valid fields.

    Excludes keys whose value is None or that appear in
    ``fundamentals.get("missing_fields", [])``.
    """
    missing = set(fundamentals.get("missing_fields", []))
    rows = []
    for key in _FUNDAMENTAL_KEYS:
        if key not in fundamentals:
            continue
        value = fundamentals[key]
        if value is None or key in missing:
            continue
        rows.append({
            "Metric": key.replace("_", " ").title(),
            "Value": f"{value:.2f}",
        })
    return rows


def _direction_icon(direction: str) -> str:
    """Return a coloured circle emoji for a pattern direction string."""
    if direction == "bullish":
        return "🟢"
    if direction == "bearish":
        return "🔴"
    return "🟡"


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------

def render(ticker: str) -> None:
    """Render the Stock Detail page for *ticker*."""

    # ------------------------------------------------------------------
    # Header + manual refresh
    # ------------------------------------------------------------------
    col_title, col_btn = st.columns([6, 1])
    with col_title:
        st.title(f"📊 {ticker}")
    with col_btn:
        if st.button("🔄 Refresh"):
            refresh_ticker_now(ticker)
            st.rerun()

    # ------------------------------------------------------------------
    # Load data — auto-refresh if stale
    # ------------------------------------------------------------------
    cache_data = read_cache(ticker)
    if cache_data is None or _is_stale(cache_data):
        refresh_ticker_now(ticker)
        cache_data = read_cache(ticker)
    if cache_data is None:
        st.error(f"Could not load data for {ticker}")
        return

    # ------------------------------------------------------------------
    # Compute scores
    # ------------------------------------------------------------------
    try:
        scores = compute_full_score(cache_data)
    except Exception as exc:
        st.error(f"Scoring failed for {ticker}: {exc}")
        return

    # ------------------------------------------------------------------
    # Score cards
    # ------------------------------------------------------------------
    def _fmt(val):
        return str(val) if val is not None else "N/A"

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Technical", _fmt(scores["technical"]))
    c2.metric("Fundamental", _fmt(scores["fundamental"]))
    c3.metric("Sentiment", _fmt(scores["sentiment"]))
    c4.metric("Final Score", _fmt(scores["final"]))
    c5.metric("Verdict", scores["verdict"])

    # ------------------------------------------------------------------
    # Price chart (candlestick)
    # ------------------------------------------------------------------
    ohlcv = cache_data.get("ohlcv", {})
    if ohlcv.get("dates"):
        fig = go.Figure(data=[go.Candlestick(
            x=ohlcv["dates"],
            open=ohlcv["open"],
            high=ohlcv["high"],
            low=ohlcv["low"],
            close=ohlcv["close"],
        )])
        fig.update_layout(
            title=f"{ticker} — 6-Month Price",
            xaxis_rangeslider_visible=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------------------------
    # Score drivers
    # ------------------------------------------------------------------
    with st.expander("📈 Technical Drivers"):
        for driver in scores.get("technical_drivers", []):
            st.write(driver)

    with st.expander("📊 Fundamental Drivers"):
        for driver in scores.get("fundamental_drivers", []):
            st.write(driver)

    with st.expander("💬 Sentiment Drivers"):
        for driver in scores.get("sentiment_drivers", []):
            st.write(driver)

    # ------------------------------------------------------------------
    # Detected patterns
    # ------------------------------------------------------------------
    st.subheader("🔍 Detected Chart Patterns")
    patterns = scores.get("patterns_detected", [])
    if not patterns:
        st.info("No patterns detected in the current window.")
    else:
        for p in patterns:
            icon = _direction_icon(p["direction"])
            st.markdown(
                f"**{icon} {p['name']}** (detected {p['detected_at']}) — Reliability: {p['reliability']}"
            )
            st.caption(p["meaning"])

    # ------------------------------------------------------------------
    # Fundamentals table
    # ------------------------------------------------------------------
    st.subheader("📋 Key Ratios")
    fundamentals = cache_data.get("fundamentals", {})
    rows = _build_fundamentals_rows(fundamentals)
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No fundamental data available.")
