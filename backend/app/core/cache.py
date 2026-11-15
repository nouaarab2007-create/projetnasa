"""A small in-memory TTL cache (thread/async safe enough for a single process)."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Least-recently-used cache whose entries expire after ``ttl`` seconds."""

    def __init__(self, ttl: float, max_entries: int = 512) -> None:
        self.ttl = ttl
        self.max_entries = max_entries
        self._items: OrderedDict[str, tuple[float, T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.monotonic():
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return value

    def set(self, key: str, value: T) -> None:
        self._items[key] = (time.monotonic() + self.ttl, value)
        self._items.move_to_end(key)
        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
