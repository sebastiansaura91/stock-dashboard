import json
import os
import pytest
from cache import write_cache, read_cache


def test_write_and_read_roundtrip(tmp_cache_dir, sample_cache_entry):
    write_cache("AAPL", sample_cache_entry, cache_dir=tmp_cache_dir)
    result = read_cache("AAPL", cache_dir=tmp_cache_dir)
    assert result["ticker"] == "AAPL"
    assert result["fundamentals"]["pe_ratio"] == 28.4


def test_read_missing_ticker_returns_none(tmp_cache_dir):
    result = read_cache("ZZZZ", cache_dir=tmp_cache_dir)
    assert result is None


def test_write_is_atomic(tmp_cache_dir, sample_cache_entry):
    # tmp file should not persist after write
    write_cache("AAPL", sample_cache_entry, cache_dir=tmp_cache_dir)
    tmp_path = os.path.join(tmp_cache_dir, "AAPL.json.tmp")
    assert not os.path.exists(tmp_path)
    assert os.path.exists(os.path.join(tmp_cache_dir, "AAPL.json"))


def test_overwrite_replaces_data(tmp_cache_dir, sample_cache_entry):
    write_cache("AAPL", sample_cache_entry, cache_dir=tmp_cache_dir)
    updated = dict(sample_cache_entry)
    updated["fetch_error"] = True
    write_cache("AAPL", updated, cache_dir=tmp_cache_dir)
    result = read_cache("AAPL", cache_dir=tmp_cache_dir)
    assert result["fetch_error"] is True
