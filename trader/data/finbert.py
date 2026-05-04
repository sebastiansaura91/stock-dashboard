"""HuggingFace Inference API client for FinBERT sentiment classification.

Replaces the local transformers pipeline with HTTP calls to the free
HuggingFace Inference API. Keeps the same classify_batch() interface
so callers (scheduler.py) work without modification.
"""

import logging
import time

import httpx

from config import HF_API_KEY, HF_API_URL, FINBERT_BATCH_SIZE

logger = logging.getLogger(__name__)

_NEUTRAL_FALLBACK = {"label": "neutral", "score": 0.0}


def classify_batch(texts: list[str]) -> list[dict]:
    """Classify *texts* using the HuggingFace Inference API.

    Returns a list of {"label": str, "score": float} dicts — one per input.
    Falls back to neutral on any error so callers never crash.
    """
    if not texts:
        return []

    results: list[dict] = []
    for i in range(0, len(texts), FINBERT_BATCH_SIZE):
        chunk = texts[i : i + FINBERT_BATCH_SIZE]
        results.extend(_classify_chunk(chunk))

    # Safety: ensure count matches (should never differ, but guard it)
    if len(results) != len(texts):
        logger.error(
            "classify_batch: result count mismatch %d vs %d",
            len(results),
            len(texts),
        )
        while len(results) < len(texts):
            results.append(dict(_NEUTRAL_FALLBACK))

    return results[: len(texts)]


def _classify_chunk(texts: list[str]) -> list[dict]:
    """Send one batch to the HF API and parse the response."""
    headers = {}
    if HF_API_KEY:
        headers["Authorization"] = f"Bearer {HF_API_KEY}"

    try:
        response = httpx.post(
            HF_API_URL,
            headers=headers,
            json={"inputs": texts},
            timeout=30.0,
        )
    except Exception:
        logger.exception("HF API request failed")
        return [dict(_NEUTRAL_FALLBACK) for _ in texts]

    # 503 = model still loading — wait once and retry
    if response.status_code == 503:
        body = response.json()
        wait = min(float(body.get("estimated_time", 20)), 60.0)
        logger.warning("HF model loading — waiting %.0fs then retrying", wait)
        time.sleep(wait)
        try:
            response = httpx.post(
                HF_API_URL,
                headers=headers,
                json={"inputs": texts},
                timeout=30.0,
            )
        except Exception:
            logger.exception("HF API retry failed")
            return [dict(_NEUTRAL_FALLBACK) for _ in texts]

    try:
        response.raise_for_status()
        raw = response.json()
    except Exception:
        logger.exception("HF API response error (status %d)", response.status_code)
        return [dict(_NEUTRAL_FALLBACK) for _ in texts]

    if not isinstance(raw, list):
        logger.error("Unexpected HF API response type: %s", type(raw))
        return [dict(_NEUTRAL_FALLBACK) for _ in texts]

    results = []
    for item in raw:
        if isinstance(item, list) and item:
            best = max(item, key=lambda x: x.get("score", 0.0))
            results.append(
                {
                    "label": best.get("label", "neutral").lower(),
                    "score": float(best.get("score", 0.0)),
                }
            )
        else:
            results.append(dict(_NEUTRAL_FALLBACK))

    return results
