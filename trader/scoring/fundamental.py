import math
import os
import json
import glob

_RATIO_CONFIG = {
    "pe_ratio":             {"weight": 0.20, "bullish": 18.0,  "bearish": 35.0,  "lower_is_better": True},
    "ev_ebitda":            {"weight": 0.20, "bullish": 12.0,  "bearish": 25.0,  "lower_is_better": True},
    "revenue_growth_yoy":   {"weight": 0.20, "bullish": 0.10,  "bearish": 0.0,   "lower_is_better": False},
    "gross_margin":         {"weight": 0.15, "bullish": 0.40,  "bearish": 0.15,  "lower_is_better": False},
    "operating_margin":     {"weight": 0.15, "bullish": 0.15,  "bearish": 0.05,  "lower_is_better": False},
    "debt_equity":          {"weight": 0.10, "bullish": 1.0,   "bearish": 3.0,   "lower_is_better": True},
}


def _score_ratio(value: float, bullish: float, bearish: float, lower_is_better: bool) -> float:
    if lower_is_better:
        bullish, bearish = bearish, bullish
    if bearish == bullish:
        return 50.0
    raw = (value - bearish) / (bullish - bearish)
    return max(0.0, min(100.0, raw * 100.0))


def _compute_sector_medians(sector: str) -> dict:
    """Compute median values per ratio from all cached tickers in the same sector."""
    from config import CACHE_DIR
    ratio_values: dict[str, list[float]] = {k: [] for k in _RATIO_CONFIG}
    for path in glob.glob(os.path.join(CACHE_DIR, "*.json")):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            fund = data.get("fundamentals", {})
            if fund.get("sector") != sector:
                continue
            for key in _RATIO_CONFIG:
                v = fund.get(key)
                if v is not None:
                    ratio_values[key].append(float(v))
        except Exception:
            continue
    medians = {}
    for key, values in ratio_values.items():
        if len(values) >= 3:
            medians[key] = sorted(values)[len(values) // 2]
    return medians


def compute_fundamental_score(fundamentals: dict) -> tuple[int | None, list[str]]:
    missing = set(fundamentals.get("missing_fields", []))
    available = {k: v for k, v in fundamentals.items() if k in _RATIO_CONFIG and k not in missing and v is not None}

    if len(available) < 3:
        return None, ["Insufficient fundamental data"]

    # Try to get sector medians; fall back to absolute thresholds if < 3 peers found
    sector = fundamentals.get("sector", "")
    sector_medians = _compute_sector_medians(sector) if sector else {}

    total_weight = sum(_RATIO_CONFIG[k]["weight"] for k in available)
    weighted_sum = 0.0
    drivers = []

    for key, value in available.items():
        cfg = _RATIO_CONFIG[key]
        median = sector_medians.get(key)
        if median is not None and median > 0:
            # Dynamic thresholds: 80% of median = bullish, 150% = bearish (for lower-is-better)
            if cfg["lower_is_better"]:
                bullish = median * 0.8
                bearish = median * 1.5
            else:
                bullish = median
                bearish = median * 0.7
        else:
            bullish = cfg["bullish"]
            bearish = cfg["bearish"]
        ratio_score = _score_ratio(value, bullish, bearish, cfg["lower_is_better"])
        weighted_sum += ratio_score * cfg["weight"]
        label = "strong" if ratio_score >= 70 else ("weak" if ratio_score <= 30 else "neutral")
        drivers.append(f"{key.replace('_', ' ').title()}: {value:.2f} ({label})")

    normalised = weighted_sum / total_weight if total_weight > 0 else 50.0
    return int(math.floor(normalised)), drivers
