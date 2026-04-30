"""Streamlit entry point. Run with:  streamlit run app.py"""
import streamlit as st
from config import WATCHLIST
from scheduler import start_scheduler
from pages import watchlist as watchlist_page
from pages import detail as detail_page
from pages import screener as screener_page


def main() -> None:
    st.set_page_config(
        page_title="Stock Dashboard",
        page_icon="📈",
        layout="wide",
    )

    # Start background scheduler (idempotent — safe to call on every rerun)
    if "watchlist" in st.session_state:
        tickers = st.session_state["watchlist"]
    else:
        tickers = list(WATCHLIST)
    start_scheduler(tickers)

    # Sidebar navigation
    st.sidebar.title("📈 Stock Dashboard")
    nav = st.sidebar.radio(
        "Navigate",
        ["Watchlist", "Screener"],
        key="nav",
    )

    # Route to page
    page = st.session_state.get("page", nav.lower())

    if page == "detail":
        ticker = st.session_state.get("selected_ticker", "AAPL")
        # Back button
        if st.sidebar.button("← Back"):
            st.session_state["page"] = None
            st.rerun()
        detail_page.render(ticker)
    elif page == "screener" or nav == "Screener":
        screener_page.render()
    else:
        watchlist_page.render()


if __name__ == "__main__":
    main()
