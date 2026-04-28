from unittest.mock import patch, MagicMock


def test_classify_returns_label_and_score():
    with patch("data.finbert._get_pipeline") as mock_pipe_fn:
        mock_pipe = MagicMock()
        mock_pipe.return_value = [[{"label": "positive", "score": 0.95}]]
        mock_pipe_fn.return_value = mock_pipe
        from data.finbert import classify_batch
        results = classify_batch(["Apple earnings beat expectations"])
    assert len(results) == 1
    assert results[0]["label"] in ("positive", "negative", "neutral")
    assert 0.0 <= results[0]["score"] <= 1.0


def test_classify_batch_handles_multiple():
    with patch("data.finbert._get_pipeline") as mock_pipe_fn:
        mock_pipe = MagicMock()
        mock_pipe.return_value = [
            [{"label": "positive", "score": 0.9}],
            [{"label": "negative", "score": 0.8}],
        ]
        mock_pipe_fn.return_value = mock_pipe
        from data.finbert import classify_batch
        results = classify_batch(["Good news", "Bad news"])
    assert len(results) == 2


def test_classify_empty_list_returns_empty():
    with patch("data.finbert._get_pipeline"):
        from data.finbert import classify_batch
        assert classify_batch([]) == []
