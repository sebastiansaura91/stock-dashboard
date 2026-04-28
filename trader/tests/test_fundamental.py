import pytest
from scoring.fundamental import compute_fundamental_score

_GOOD_FUNDAMENTALS = {
    "pe_ratio": 15.0,
    "ev_ebitda": 10.0,
    "revenue_growth_yoy": 0.15,
    "gross_margin": 0.50,
    "operating_margin": 0.20,
    "debt_equity": 0.5,
    "sector": "Technology",
    "missing_fields": [],
}

_BAD_FUNDAMENTALS = {
    "pe_ratio": 80.0,
    "ev_ebitda": 40.0,
    "revenue_growth_yoy": -0.05,
    "gross_margin": 0.10,
    "operating_margin": 0.02,
    "debt_equity": 5.0,
    "sector": "Technology",
    "missing_fields": [],
}


def test_score_is_int_in_range():
    score, _ = compute_fundamental_score(_GOOD_FUNDAMENTALS)
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_good_fundamentals_score_higher_than_bad():
    good_score, _ = compute_fundamental_score(_GOOD_FUNDAMENTALS)
    bad_score, _ = compute_fundamental_score(_BAD_FUNDAMENTALS)
    assert good_score > bad_score


def test_missing_field_excluded_from_score():
    fund = dict(_GOOD_FUNDAMENTALS)
    fund["pe_ratio"] = None
    fund["missing_fields"] = ["pe_ratio"]
    score, drivers = compute_fundamental_score(fund)
    assert score is not None
    assert 0 <= score <= 100


def test_too_many_missing_returns_none():
    fund = {k: None for k in _GOOD_FUNDAMENTALS}
    fund["sector"] = "Technology"
    fund["missing_fields"] = ["pe_ratio", "ev_ebitda", "revenue_growth_yoy", "gross_margin"]
    score, _ = compute_fundamental_score(fund)
    assert score is None


def test_drivers_is_list_of_strings():
    _, drivers = compute_fundamental_score(_GOOD_FUNDAMENTALS)
    assert isinstance(drivers, list)
    assert all(isinstance(d, str) for d in drivers)
