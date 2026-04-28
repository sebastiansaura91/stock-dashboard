import math
from datetime import datetime, timezone
from config import SENTIMENT_LOOKBACK_HOURS, SENTIMENT_HALF_LIFE_HOURS

_LABEL_SCORE = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}
# Items with no timestamp get a fixed low weight rather than being excluded entirely.
# Must stay low relative to a fresh item weight (~0.92) so that no-timestamp items
# cannot overwhelm timestamped items even when numerous.
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
    contributing_count = 0
    # Count contributing items by label (only those with weight > 0)
    label_counts: dict[str, int] = {"positive": 0, "negative": 0, "neutral": 0}

    for item in items:
        label = (item.get("label") or "neutral").lower()
        label_score = _LABEL_SCORE.get(label, 0.5)
        weight = _age_weight(item.get("published_at"))
        if weight == 0.0:
            continue
        weighted_sum += label_score * weight
        weight_total += weight
        contributing_count += 1
        if label in label_counts:
            label_counts[label] += 1

    if weight_total == 0 or contributing_count < 3:
        return None, ["Insufficient recent sentiment data"]

    score = (weighted_sum / weight_total) * 100
    clamped = max(0, min(100, int(math.floor(score))))

    drivers = [
        f"{label_counts['positive']} bullish / {label_counts['negative']} bearish / "
        f"{label_counts['neutral']} neutral items in last {SENTIMENT_LOOKBACK_HOURS}h"
    ]

    return clamped, drivers
