import time
import logging
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]
_ua_index = 0


def _next_ua() -> str:
    global _ua_index
    ua = _USER_AGENTS[_ua_index % len(_USER_AGENTS)]
    _ua_index += 1
    return ua


def _retry_get(url: str, max_retries: int = 3, base_delay: float = 1.0, **kwargs):
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=10, **kwargs)
            if resp.status_code in (429, 403):
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                return None
            return resp
        except Exception as e:
            logger.warning("GET %s attempt %d failed: %s", url, attempt + 1, e)
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
    return None


def _parse_dt(dt_str: str | None) -> str | None:
    if not dt_str:
        return None
    try:
        return parsedate_to_datetime(dt_str).astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).isoformat()
    except Exception:
        return None


def fetch_google_news(ticker: str) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries:
        items.append({
            "source": "google_news",
            "headline": e.get("title", ""),
            "published_at": _parse_dt(e.get("published")),
            "label": None,
            "score": None,
        })
    return items


def fetch_stocktwits(ticker: str) -> list[dict]:
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    resp = _retry_get(url)
    if resp is None:
        return []
    try:
        messages = resp.json().get("messages", [])
    except Exception:
        return []
    return [
        {
            "source": "stocktwits",
            "headline": m.get("body", ""),
            "published_at": _parse_dt(m.get("created_at")),
            "label": None,
            "score": None,
        }
        for m in messages
    ]


def fetch_reddit_rss(ticker: str, subreddit: str) -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/search.rss?q={ticker}&sort=new"
    feed = feedparser.parse(url)
    return [
        {
            "source": f"reddit_{subreddit}",
            "headline": e.get("title", ""),
            "published_at": _parse_dt(e.get("published")),
            "label": None,
            "score": None,
        }
        for e in feed.entries
    ]


def fetch_finviz(ticker: str) -> list[dict]:
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    headers = {"User-Agent": _next_ua()}
    time.sleep(2)
    resp = _retry_get(url, headers=headers)
    if resp is None:
        logger.warning("Finviz blocked for %s — skipping", ticker)
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("table.fullview-news-outer tr")
    items = []
    for row in rows:
        link = row.find("a")
        if link:
            items.append({
                "source": "finviz",
                "headline": link.get_text(strip=True),
                "published_at": None,
                "label": None,
                "score": None,
            })
    return items


def fetch_all_sentiment(ticker: str) -> list[dict]:
    items = []
    items.extend(fetch_google_news(ticker))
    items.extend(fetch_stocktwits(ticker))
    items.extend(fetch_reddit_rss(ticker, "stocks"))
    items.extend(fetch_reddit_rss(ticker, "investing"))
    items.extend(fetch_finviz(ticker))
    return items
