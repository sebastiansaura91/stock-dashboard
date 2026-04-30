"""Cache read/write with portalocker file locking and atomic rename."""

import json
import os
import portalocker


def _cache_path(ticker: str, cache_dir: str) -> str:
    return os.path.join(cache_dir, f"{ticker}.json")


def write_cache(ticker: str, data: dict, cache_dir: str = None) -> None:
    from config import CACHE_DIR
    if cache_dir is None:
        cache_dir = CACHE_DIR
    os.makedirs(cache_dir, exist_ok=True)
    path = _cache_path(ticker, cache_dir)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        json.dump(data, f, default=str)
        f.flush()
        os.fsync(f.fileno())
        portalocker.unlock(f)
    # Rename outside the context manager so no lock is held during os.replace.
    # On Windows, os.replace raises PermissionError if the destination is open by
    # another process (e.g. a concurrent read_cache call holding a shared lock).
    os.replace(tmp_path, path)


def read_cache(ticker: str, cache_dir: str = None) -> dict | None:
    from config import CACHE_DIR
    if cache_dir is None:
        cache_dir = CACHE_DIR
    path = _cache_path(ticker, cache_dir)
    try:
        with open(path, "r", encoding="utf-8") as f:
            portalocker.lock(f, portalocker.LOCK_SH)
            data = json.load(f)
            portalocker.unlock(f)
        return data
    except FileNotFoundError:
        return None
