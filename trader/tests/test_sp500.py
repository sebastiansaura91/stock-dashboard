"""Tests for data/build_sp500.py."""
import csv
import os
from unittest.mock import MagicMock, patch

import pytest

# Adjust import path so tests can find build_sp500 regardless of cwd.
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from build_sp500 import fetch_sp500_tickers, write_csv


def test_write_csv_creates_file(tmp_path):
    """write_csv creates a file with the correct header and ticker rows."""
    dest = str(tmp_path / "sp500.csv")
    tickers = ["AAPL", "MSFT", "NVDA"]
    write_csv(tickers, dest)

    assert os.path.exists(dest)

    with open(dest, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert rows[0] == ["ticker"], "First row must be the header"
    assert rows[1] == ["AAPL"]
    assert rows[2] == ["MSFT"]
    assert rows[3] == ["NVDA"]
    assert len(rows) == 4  # header + 3 tickers


def test_ticker_dot_to_hyphen():
    """fetch_sp500_tickers replaces dots with hyphens (BRK.B -> BRK-B)."""
    fake_html = """
    <html><body>
    <table id="constituents">
      <tr><th>Symbol</th></tr>
      <tr><td>BRK.B</td></tr>
      <tr><td>AAPL</td></tr>
    </table>
    </body></html>
    """
    mock_response = MagicMock()
    mock_response.text = fake_html
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        tickers = fetch_sp500_tickers()

    assert "BRK-B" in tickers, "BRK.B should be converted to BRK-B"
    assert "BRK.B" not in tickers, "Dot form should not appear in output"
    assert "AAPL" in tickers
