"""Smoke tests — verify imports and basic structure without executing Streamlit rendering."""
from unittest.mock import patch


def test_app_imports():
    """Import app; assert main is callable. Patch out st.set_page_config and start_scheduler."""
    with patch("streamlit.set_page_config"), patch("scheduler.start_scheduler"):
        import app
        assert callable(app.main)


def test_watchlist_page_imports():
    """Verify watchlist page exposes the expected callables."""
    from pages.watchlist import render, _is_stale, colour_verdict
    assert callable(render)
    assert callable(_is_stale)
    assert callable(colour_verdict)


def test_detail_page_imports():
    """Verify detail page exposes the expected callables."""
    from pages.detail import render, _build_fundamentals_rows, _direction_icon
    assert callable(render)
    assert callable(_build_fundamentals_rows)
    assert callable(_direction_icon)


def test_screener_page_imports():
    """Verify screener page exposes the expected callables."""
    from pages.screener import render, _apply_filters, _load_universe
    assert callable(render)
    assert callable(_apply_filters)
    assert callable(_load_universe)


def test_scoring_engine_imports():
    """Verify the scoring engine exposes compute_full_score."""
    from scoring.engine import compute_full_score
    assert callable(compute_full_score)
