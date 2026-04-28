import math
from config import DEFAULT_WEIGHTS
from scoring.technical import compute_technical_score
from scoring.fundamental import compute_fundamental_score
from scoring.sentiment_score import compute_sentiment_score


def _verdict(score: int) -> str:
    if score >= 75:
        return "Strong BUY"
    if score >= 60:
        return "BUY"
    if score >= 45:
        return "HOLD"
    if score >= 30:
        return "SELL"
    return "Strong SELL"


def compute_full_score(cache_data: dict, weights: dict = None) -> dict:
    weights = weights or DEFAULT_WEIGHTS

    # Support test overrides
    overrides = cache_data.get("_override_scores", {})

    if "technical" in overrides:
        tech_score = overrides["technical"]
        tech_drivers = []
        patterns = []
    else:
        tech_score, tech_drivers, patterns = compute_technical_score(cache_data.get("ohlcv", {}))

    if "fundamental" in overrides:
        fund_score = overrides["fundamental"]
        fund_drivers = []
    else:
        fund_score, fund_drivers = compute_fundamental_score(cache_data.get("fundamentals", {}))

    if "sentiment" in overrides:
        sent_score = overrides["sentiment"]
        sent_drivers = []
    else:
        sent_score, sent_drivers = compute_sentiment_score(cache_data.get("sentiment_items", []))

    sub_scores = {
        "technical": (tech_score, weights["technical"]),
        "fundamental": (fund_score, weights["fundamental"]),
        "sentiment": (sent_score, weights["sentiment"]),
    }

    available = {k: (s, w) for k, (s, w) in sub_scores.items() if s is not None}
    if not available:
        final = None
        verdict = "HOLD"
    else:
        total_weight = sum(w for _, w in available.values())
        weighted_sum = sum(s * w for s, w in available.values())
        final = int(math.floor(weighted_sum / total_weight))
        verdict = _verdict(final)

    return {
        "technical": tech_score,
        "fundamental": fund_score,
        "sentiment": sent_score,
        "final": final,
        "verdict": verdict,
        "patterns_detected": patterns,
        "technical_drivers": tech_drivers,
        "fundamental_drivers": fund_drivers,
        "sentiment_drivers": sent_drivers,
    }
