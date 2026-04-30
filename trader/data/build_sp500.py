"""Regenerate data/sp500.csv from Wikipedia's S&P 500 list.

Usage:
    python data/build_sp500.py
"""
import csv
import os
import requests
from bs4 import BeautifulSoup

_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_OUTPUT = os.path.join(os.path.dirname(__file__), "sp500.csv")


def fetch_sp500_tickers() -> list[str]:
    """Scrape S&P 500 ticker symbols from Wikipedia."""
    resp = requests.get(_WIKI_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"id": "constituents"})
    tickers = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if cells:
            raw = cells[0].text.strip()
            # Wikipedia uses dots; Yahoo Finance uses hyphens (e.g., BRK.B → BRK-B)
            tickers.append(raw.replace(".", "-"))
    return tickers


def write_csv(tickers: list[str], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker"])
        for t in tickers:
            writer.writerow([t])
    print(f"Wrote {len(tickers)} tickers to {path}")


if __name__ == "__main__":
    tickers = fetch_sp500_tickers()
    write_csv(tickers, _OUTPUT)
