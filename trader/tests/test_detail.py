"""Tests for pages/detail.py helper functions (no Streamlit rendering required)."""

import pytest
from pages.detail import _build_fundamentals_rows, _direction_icon


# ---------------------------------------------------------------------------
# _build_fundamentals_rows
# ---------------------------------------------------------------------------

def test_format_fundamental_row_skips_none():
    fundamentals = {"pe_ratio": 15.0, "ev_ebitda": None, "missing_fields": []}
    rows = _build_fundamentals_rows(fundamentals)
    metrics = [r["Metric"] for r in rows]
    assert "Pe Ratio" in metrics
    assert "Ev Ebitda" not in metrics
    assert len(rows) == 1


def test_format_fundamental_row_skips_missing_fields():
    fundamentals = {"pe_ratio": 15.0, "ev_ebitda": 10.0, "missing_fields": ["ev_ebitda"]}
    rows = _build_fundamentals_rows(fundamentals)
    metrics = [r["Metric"] for r in rows]
    assert "Pe Ratio" in metrics
    assert "Ev Ebitda" not in metrics
    assert len(rows) == 1


def test_format_fundamental_row_formats_floats():
    fundamentals = {"pe_ratio": 15.12345, "missing_fields": []}
    rows = _build_fundamentals_rows(fundamentals)
    assert len(rows) == 1
    assert rows[0]["Value"] == "15.12"


# ---------------------------------------------------------------------------
# _direction_icon
# ---------------------------------------------------------------------------

def test_direction_icon_bullish():
    assert _direction_icon("bullish") == "🟢"


def test_direction_icon_bearish():
    assert _direction_icon("bearish") == "🔴"


def test_direction_icon_neutral():
    assert _direction_icon("neutral") == "🟡"
    assert _direction_icon("unknown") == "🟡"
    assert _direction_icon("") == "🟡"
