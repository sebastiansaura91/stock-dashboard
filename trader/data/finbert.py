import logging
from config import FINBERT_BATCH_SIZE

logger = logging.getLogger(__name__)

_pipeline = None
_load_failed = False


def _get_pipeline():
    global _pipeline, _load_failed
    if _pipeline is not None:
        return _pipeline
    if _load_failed:
        return None
    try:
        from transformers import pipeline
        _pipeline = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            device=-1,  # CPU
            top_k=1,
        )
        logger.info("FinBERT loaded successfully")
    except Exception as e:
        logger.error("FinBERT failed to load: %s", e)
        _load_failed = True
        return None
    return _pipeline


def classify_batch(texts: list[str]) -> list[dict]:
    if not texts:
        return []
    pipe = _get_pipeline()
    if pipe is None:
        return [{"label": "neutral", "score": 0.0} for _ in texts]
    results = []
    for i in range(0, len(texts), FINBERT_BATCH_SIZE):
        batch = texts[i : i + FINBERT_BATCH_SIZE]
        try:
            outputs = pipe(batch)
            for out in outputs:
                top = out[0] if isinstance(out, list) else out
                results.append({"label": top["label"].lower(), "score": round(top["score"], 4)})
        except Exception as e:
            logger.error("FinBERT inference error: %s", e)
            results.extend([{"label": "neutral", "score": 0.0} for _ in batch])
    return results
