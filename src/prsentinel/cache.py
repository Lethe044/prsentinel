"""A tiny on-disk cache keyed by the hash of a diff chunk plus the provider
and model used to review it.

This exists for one practical reason: GitHub Actions re-runs and repeated
local `prsentinel review` calls on the same commit should not burn through a
free tier API quota reviewing the exact same lines twice.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

CACHE_DIR_NAME = ".prsentinel_cache"
CACHE_VERSION = 1


def _cache_dir() -> Path:
    directory = Path.cwd() / CACHE_DIR_NAME
    directory.mkdir(exist_ok=True)
    return directory


def make_key(chunk_text: str, provider: str, model: str) -> str:
    payload = f"{CACHE_VERSION}:{provider}:{model}:{chunk_text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def get(key: str) -> Optional[str]:
    path = _cache_dir() / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("response")
    except (json.JSONDecodeError, OSError):
        return None


def set(key: str, response: str) -> None:
    path = _cache_dir() / f"{key}.json"
    try:
        path.write_text(json.dumps({"response": response}), encoding="utf-8")
    except OSError:
        # Caching is a nice to have. A read only filesystem or a full disk
        # should never break a review run.
        pass


def clear() -> int:
    directory = _cache_dir()
    removed = 0
    for item in directory.glob("*.json"):
        item.unlink()
        removed += 1
    return removed


def stats() -> dict:
    """Returns a small, honest snapshot of the local cache: how many
    responses are stored, how much disk space they use, and the directory
    they live in. Nothing here is inferred or estimated.
    """

    directory = _cache_dir()
    entries = list(directory.glob("*.json"))
    total_bytes = sum(entry.stat().st_size for entry in entries)

    return {
        "directory": str(directory),
        "entry_count": len(entries),
        "total_bytes": total_bytes,
    }
