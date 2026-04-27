import yfinance as yf


_FUNDAMENTAL_MAP = {
    "pe_ratio": "trailingPE",
    "ev_ebitda": "enterpriseToEbitda",
    "revenue_growth_yoy": "revenueGrowth",
    "gross_margin": "grossMargins",
    "operating_margin": "operatingMargins",
    "debt_equity": lambda info: (info["debtToEquity"] / 100) if info.get("debtToEquity") is not None else None,
    "sector": "sector",
}


def fetch_ohlcv(ticker: str, period: str = "6mo") -> dict:
    tk = yf.Ticker(ticker)
    hist = tk.history(period=period)
    _required = {"Open", "High", "Low", "Close", "Volume"}
    if hist.empty or not _required.issubset(hist.columns):
        return {k: [] for k in ("dates", "open", "high", "low", "close", "volume")}
    return {
        "dates": hist.index.strftime("%Y-%m-%d").tolist(),
        "open": hist["Open"].round(4).tolist(),
        "high": hist["High"].round(4).tolist(),
        "low": hist["Low"].round(4).tolist(),
        "close": hist["Close"].round(4).tolist(),
        "volume": hist["Volume"].astype(int).tolist(),
    }


def fetch_fundamentals(ticker: str) -> dict:
    tk = yf.Ticker(ticker)
    info = tk.info or {}
    result = {}
    missing = []
    for key, src in _FUNDAMENTAL_MAP.items():
        if callable(src):
            val = src(info)
        else:
            val = info.get(src)
        if val is None and key != "sector":
            missing.append(key)
        result[key] = val
    result["missing_fields"] = missing
    return result
