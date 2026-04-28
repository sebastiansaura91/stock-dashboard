import pytest
from scoring.engine import compute_full_score


def make_cache(tech=70, fund=65, sent=60):
    return {
        "ohlcv": {"dates": [], "open": [], "high": [], "low": [], "close": [], "volume": []},
        "fundamentals": {
            "pe_ratio": 15.0, "ev_ebitda": 10.0, "revenue_growth_yoy": 0.15,
            "gross_margin": 0.5, "operating_margin": 0.2, "debt_equity": 0.5,
            "sector": "Technology", "missing_fields": [],
        },
        "sentiment_items": [],
        "_override_scores": {"technical": tech, "fundamental": fund, "sentiment": sent},
    }


def test_final_score_is_weighted_average():
    # With equal override scores the final should equal them
    result = compute_full_score(make_cache(tech=60, fund=60, sent=60))
    assert result["final"] == 60


def test_verdict_buy_at_65():
    result = compute_full_score(make_cache(tech=65, fund=65, sent=65))
    assert result["verdict"] == "BUY"


def test_verdict_strong_buy_at_80():
    result = compute_full_score(make_cache(tech=80, fund=80, sent=80))
    assert result["verdict"] == "Strong BUY"


def test_verdict_sell_at_35():
    result = compute_full_score(make_cache(tech=35, fund=35, sent=35))
    assert result["verdict"] == "SELL"


def test_verdict_strong_sell_at_20():
    result = compute_full_score(make_cache(tech=20, fund=20, sent=20))
    assert result["verdict"] == "Strong SELL"


def test_null_sub_score_excluded_from_final():
    result = compute_full_score(make_cache(tech=80, fund=None, sent=80))
    # Only tech(40%) and sent(25%) remain, renormalised to 100%
    assert result["final"] is not None
    assert result["fundamental"] is None


def test_result_has_required_keys():
    result = compute_full_score(make_cache())
    for key in ("technical", "fundamental", "sentiment", "final", "verdict",
                 "patterns_detected", "technical_drivers", "fundamental_drivers", "sentiment_drivers"):
        assert key in result
