import json
import os
import portalocker


def _cache_path(ticker: str, cache_dir: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{ticker}.json")


def write_cache(ticker: str, data: dict, cache_dir: str = None) -> None:
    from config import CACHE_DIR
    if cache_dir is None:
        cache_dir = CACHE_DIR
    path = _cache_path(ticker, cache_dir)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        json.dump(data, f, default=str)
    os.replace(tmp_path, path)


def read_cache(ticker: str, cache_dir: str = None) -> dict | None:
    from config import CACHE_DIR
    if cache_dir is None:
        cache_dir = CACHE_DIR
    path = _cache_path(ticker, cache_dir)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        portalocker.lock(f, portalocker.LOCK_SH)
        data = json.load(f)
        portalocker.unlock(f)
    return data
