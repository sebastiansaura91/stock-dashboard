"""Unit tests for scheduler.py.

All external dependencies (Streamlit, fetchers, cache, APScheduler) are mocked
so these tests exercise only the scheduler's own logic.
"""

import unittest
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_state():
    """Return a plain dict that behaves like st.session_state for .get / del / []."""
    return {}


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestRefreshTickerWritesCache(unittest.TestCase):
    """refresh_ticker should fetch all data and write a single cache entry."""

    @patch("scheduler.write_cache")
    @patch("scheduler.classify_batch", return_value=[])
    @patch("scheduler.fetch_all_sentiment", return_value=[])
    @patch("scheduler.fetch_fundamentals", return_value={"pe_ratio": 20.0})
    @patch("scheduler.fetch_ohlcv", return_value={"close": [100.0]})
    def test_refresh_ticker_writes_cache(
        self, mock_ohlcv, mock_fundamentals, mock_sentiment, mock_classify, mock_write
    ):
        from scheduler import refresh_ticker

        refresh_ticker("AAPL")

        mock_write.assert_called_once()
        args, _kwargs = mock_write.call_args
        assert args[0] == "AAPL", "write_cache should be called with the ticker as first arg"
        cache_data = args[1]
        assert "ohlcv" in cache_data
        assert "fundamentals" in cache_data
        assert "sentiment_items" in cache_data
        assert "fetched_at" in cache_data


class TestRefreshTickerClassifiesUnlabelledItems(unittest.TestCase):
    """Items without a label are classified; items with a label are not re-classified."""

    @patch("scheduler.write_cache")
    @patch("scheduler.classify_batch")
    @patch("scheduler.fetch_all_sentiment")
    @patch("scheduler.fetch_fundamentals", return_value={})
    @patch("scheduler.fetch_ohlcv", return_value={})
    def test_refresh_ticker_classifies_unlabelled_items(
        self, mock_ohlcv, mock_fundamentals, mock_sentiment, mock_classify, mock_write
    ):
        from scheduler import refresh_ticker

        already_labelled = {
            "headline": "Existing label",
            "label": "positive",
            "score": 0.9,
        }
        needs_label_1 = {"headline": "No label yet", "label": None, "score": None}
        needs_label_2 = {"headline": "Also no label", "score": None}  # 'label' key absent

        mock_sentiment.return_value = [already_labelled, needs_label_1, needs_label_2]
        mock_classify.return_value = [
            {"label": "neutral", "score": 0.5},
            {"label": "negative", "score": 0.7},
        ]

        refresh_ticker("MSFT")

        # classify_batch should have been called with exactly the two unlabelled headlines
        mock_classify.assert_called_once_with(["No label yet", "Also no label"])

        # Confirm the labelled item is written with its original label unchanged
        _args, _kwargs = mock_write.call_args
        written_items = _args[1]["sentiment_items"]
        labelled_item = next(i for i in written_items if i["headline"] == "Existing label")
        assert labelled_item["label"] == "positive"

        # Confirm the previously unlabelled items now have labels
        item1 = next(i for i in written_items if i["headline"] == "No label yet")
        assert item1["label"] == "neutral"
        item2 = next(i for i in written_items if i["headline"] == "Also no label")
        assert item2["label"] == "negative"


class TestRefreshTickerCatchesExceptions(unittest.TestCase):
    """refresh_ticker must not raise even when a fetcher throws."""

    @patch("scheduler.write_cache")
    @patch("scheduler.fetch_all_sentiment", return_value=[])
    @patch("scheduler.fetch_fundamentals", return_value={})
    @patch("scheduler.fetch_ohlcv", side_effect=RuntimeError("network down"))
    def test_refresh_ticker_catches_exceptions(
        self, mock_ohlcv, mock_fundamentals, mock_sentiment, mock_write
    ):
        from scheduler import refresh_ticker
        import logging

        with self.assertLogs("scheduler", level="ERROR") as log_ctx:
            # Should not raise
            refresh_ticker("NVDA")

        # write_cache should NOT have been called because ohlcv raised
        mock_write.assert_not_called()

        # At least one ERROR log entry should mention the ticker
        error_messages = [r for r in log_ctx.output if "ERROR" in r]
        assert any("NVDA" in msg for msg in error_messages), (
            "Expected an ERROR log entry mentioning the ticker"
        )


class TestStartSchedulerAddsJobs(unittest.TestCase):
    """start_scheduler should call add_job once per ticker."""

    @patch("scheduler.BackgroundScheduler")
    def test_start_scheduler_adds_jobs(self, MockScheduler):
        from scheduler import start_scheduler

        mock_instance = MagicMock()
        mock_instance.running = False
        MockScheduler.return_value = mock_instance

        session_state = _make_session_state()

        with patch("scheduler.st") as mock_st:
            mock_st.session_state = session_state
            start_scheduler(["AAPL", "MSFT", "NVDA"])

        assert mock_instance.add_job.call_count == 3, (
            "add_job should be called once per ticker"
        )

        job_ids = [c.kwargs["id"] for c in mock_instance.add_job.call_args_list]
        assert set(job_ids) == {"refresh_AAPL", "refresh_MSFT", "refresh_NVDA"}

        for c in mock_instance.add_job.call_args_list:
            assert c.kwargs.get("replace_existing") is True, (
                "replace_existing must be True for idempotency"
            )


class TestStartSchedulerIsIdempotent(unittest.TestCase):
    """Calling start_scheduler twice with the same tickers starts the scheduler only once."""

    @patch("scheduler.BackgroundScheduler")
    def test_start_scheduler_is_idempotent(self, MockScheduler):
        from scheduler import start_scheduler

        mock_instance = MagicMock()
        # Simulate: not running before first call, running after first call.
        mock_instance.running = False
        MockScheduler.return_value = mock_instance

        session_state = _make_session_state()

        with patch("scheduler.st") as mock_st:
            mock_st.session_state = session_state

            # First call — scheduler not running, should start it.
            start_scheduler(["AAPL"])
            # Simulate the scheduler now being running.
            mock_instance.running = True

            # Second call — scheduler already running, should NOT start again.
            start_scheduler(["AAPL"])

        assert mock_instance.start.call_count == 1, (
            "scheduler.start() should only be called once even if start_scheduler is called twice"
        )


if __name__ == "__main__":
    unittest.main()
