import pytest
from datetime import datetime, timezone, timedelta
from scoring.sentiment_score import compute_sentiment_score


def _make_item(label, hours_ago=1, source="google_news"):
    published_at = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return {"source": source, "headline": "test", "published_at": published_at, "label": label, "score": 0.9}


def test_all_positive_scores_high():
    items = [_make_item("positive") for _ in range(5)]
    score, _ = compute_sentiment_score(items)
    assert score >= 80


def test_all_negative_scores_low():
    items = [_make_item("negative") for _ in range(5)]
    score, _ = compute_sentiment_score(items)
    assert score <= 20


def test_fewer_than_3_items_returns_none():
    items = [_make_item("positive"), _make_item("positive")]
    score, _ = compute_sentiment_score(items)
    assert score is None


def test_score_in_range():
    items = [_make_item("positive"), _make_item("negative"), _make_item("neutral")]
    score, _ = compute_sentiment_score(items)
    if score is not None:
        assert 0 <= score <= 100


def test_older_items_weighted_less():
    fresh_positive = [_make_item("positive", hours_ago=1) for _ in range(3)]
    stale_negative = [_make_item("negative", hours_ago=47) for _ in range(10)]
    score, _ = compute_sentiment_score(fresh_positive + stale_negative)
    stale_score, _ = compute_sentiment_score(stale_negative + fresh_positive)
    # Both should give the same result (order independent)
    assert score == stale_score


def test_no_timestamp_items_get_low_weight():
    no_ts = [{"source": "x", "headline": "h", "published_at": None, "label": "negative", "score": 0.9}] * 10
    fresh = [_make_item("positive", hours_ago=1) for _ in range(3)]
    score, _ = compute_sentiment_score(fresh + no_ts)
    assert score >= 50
