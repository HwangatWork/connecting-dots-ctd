"""
Global data source registry.
Providers write here after each fetch; /api/v1/status reads it.
"""
import time
from datetime import datetime, timezone
from typing import Any

_registry: dict[str, dict] = {}


def record(key: str, source: str, is_fallback: bool, value_hint: Any = None) -> None:
    _registry[key] = {
        "source": source,
        "is_fallback": is_fallback,
        "last_updated_ts": time.time(),
        "value_hint": str(value_hint)[:80] if value_hint is not None else None,
    }


def get_all() -> dict[str, dict]:
    return dict(_registry)


def get_status(key: str) -> dict:
    entry = _registry.get(key)
    if entry is None:
        return {"status": "미수집", "source": "—", "last_updated": None, "is_fallback": None, "value_hint": None}
    ts = entry["last_updated_ts"]
    iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return {
        "status": "폴백" if entry["is_fallback"] else "정상",
        "source": entry["source"],
        "last_updated": iso,
        "is_fallback": entry["is_fallback"],
        "value_hint": entry.get("value_hint"),
    }


def any_collected(*keys: str) -> bool:
    """Return True if at least one of the given keys is in registry as non-fallback."""
    return any(not _registry[k]["is_fallback"] for k in keys if k in _registry)


def any_registered(*keys: str) -> bool:
    return any(k in _registry for k in keys)
