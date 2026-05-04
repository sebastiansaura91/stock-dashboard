from unittest.mock import patch, MagicMock


def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx
        mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock
        )
    return mock


def test_classify_batch_returns_correct_labels():
    hf_response = [
        [{"label": "positive", "score": 0.9}, {"label": "negative", "score": 0.05}, {"label": "neutral", "score": 0.05}],
        [{"label": "negative", "score": 0.8}, {"label": "positive", "score": 0.1}, {"label": "neutral", "score": 0.1}],
    ]
    with patch("data.finbert.httpx.post", return_value=_mock_response(hf_response)):
        from data.finbert import classify_batch
        results = classify_batch(["Good news", "Bad news"])
    assert len(results) == 2
    assert results[0]["label"] == "positive"
    assert results[1]["label"] == "negative"
    assert 0.0 <= results[0]["score"] <= 1.0


def test_classify_batch_empty_returns_empty():
    from data.finbert import classify_batch
    assert classify_batch([]) == []


def test_classify_batch_falls_back_on_error():
    with patch("data.finbert.httpx.post", side_effect=Exception("network error")):
        from data.finbert import classify_batch
        results = classify_batch(["some text"])
    assert len(results) == 1
    assert results[0]["label"] == "neutral"
    assert results[0]["score"] == 0.0


def test_classify_batch_retries_on_503():
    """On HTTP 503 (model loading), sleep and retry once."""
    loading_response = _mock_response({"error": "loading", "estimated_time": 5}, 503)
    success_response = _mock_response(
        [[{"label": "neutral", "score": 0.9}, {"label": "positive", "score": 0.05}, {"label": "negative", "score": 0.05}]],
        200,
    )
    with patch("data.finbert.httpx.post", side_effect=[loading_response, success_response]):
        with patch("data.finbert.time.sleep"):
            from data.finbert import classify_batch
            results = classify_batch(["hello"])
    assert results[0]["label"] == "neutral"
