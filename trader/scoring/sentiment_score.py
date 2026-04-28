import math
from datetime import datetime, timezone
from config import SENTIMENT_LOOKBACK_HOURS, SENTIMENT_HALF_LIFE_HOURS

_LABEL_SCORE = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}
_NO_TIMESTAMP_WEIGHT = 0.1


def _age_weight(published_at: str | None) -> float:
    if not published_at:
        return _NO_TIMESTAMP_WEIGHT
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        if age_hours > SENTIMENT_LOOKBACK_HOURS:
            return 0.0
        return math.exp(-age_hours / SENTIMENT_HALF_LIFE_HOURS)
    except Exception:
        return _NO_TIMESTAMP_WEIGHT


def compute_sentiment_score(items: list[dict]) -> tuple[int | None, list[str]]:
    weighted_sum = 0.0
    weight_total = 0.0

    for item in items:
        label = (item.get("label") or "neutral").lower()
        label_score = _LABEL_SCORE.get(label, 0.5)
        weight = _age_weight(item.get("published_at"))
        if weight == 0.0:
            continue
        weighted_sum += label_score * weight
        weight_total += weight

    if weight_total == 0 or len([i for i in items if _age_weight(i.get("published_at")) > 0]) < 3:
        return None, ["Insufficient recent sentiment data"]

    score = (weighted_sum / weight_total) * 100
    clamped = max(0, min(100, int(math.floor(score))))

    bullish = sum(1 for i in items if i.get("label") == "positive")
    bearish = sum(1 for i in items if i.get("label") == "negative")
    neutral = sum(1 for i in items if i.get("label") == "neutral")
    drivers = [f"{bullish} bullish / {bearish} bearish / {neutral} neutral items in last {SENTIMENT_LOOKBACK_HOURS}h"]

    return clamped, drivers
