from unittest.mock import patch, MagicMock


def test_get_scheduler_returns_singleton():
    import importlib
    import scheduler as sched_mod
    # Reset singleton for test isolation
    sched_mod._scheduler = None
    s1 = sched_mod.get_scheduler()
    s2 = sched_mod.get_scheduler()
    assert s1 is s2


def test_start_scheduler_adds_job_and_starts():
    import scheduler as sched_mod
    mock_scheduler = MagicMock()
    mock_scheduler.running = False
    with patch.object(sched_mod, "get_scheduler", return_value=mock_scheduler):
        sched_mod.start_scheduler()
    mock_scheduler.add_job.assert_called_once()
    mock_scheduler.start.assert_called_once()


def test_stop_scheduler_calls_shutdown():
    import scheduler as sched_mod
    mock_scheduler = MagicMock()
    mock_scheduler.running = True
    with patch.object(sched_mod, "get_scheduler", return_value=mock_scheduler):
        sched_mod.stop_scheduler()
    mock_scheduler.shutdown.assert_called_once_with(wait=False)


def test_refresh_ticker_writes_cache_on_success():
    with (
        patch("scheduler.fetch_ohlcv", return_value={"close": [100.0]}),
        patch("scheduler.fetch_fundamentals", return_value={}),
        patch("scheduler.fetch_all_sentiment", return_value=[]),
        patch("scheduler.write_cache") as mock_write,
    ):
        from scheduler import refresh_ticker
        refresh_ticker("AAPL")
    mock_write.assert_called_once()
    call_args = mock_write.call_args[0]
    assert call_args[0] == "AAPL"
    assert "ohlcv" in call_args[1]
    assert "fetched_at" in call_args[1]
