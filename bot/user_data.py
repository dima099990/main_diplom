"""In-memory state and data storage for VK bot users."""
from typing import Any

_store: dict[int, dict[str, Any]] = {}


def get(uid: int) -> dict[str, Any]:
    """Return mutable data dict for user (creates if absent)."""
    return _store.setdefault(uid, {})


def state(uid: int) -> str | None:
    """Return current state key for user, or None."""
    return _store.get(uid, {}).get("_state")


def set_state(uid: int, new_state: str | None, **kwargs: Any) -> None:
    """Set state and optionally store extra data fields."""
    d = _store.setdefault(uid, {})
    d["_state"] = new_state
    d.update(kwargs)


def update(uid: int, **kwargs: Any) -> None:
    """Update data fields without changing state."""
    _store.setdefault(uid, {}).update(kwargs)


def clear(uid: int) -> None:
    """Remove all data for user (end of flow)."""
    _store.pop(uid, None)
