"""A small bounded, thread-safe cache for values derived from immutable inputs.

Keys must identify the input completely (an immutable revision ID, or a file signature of path, size and
modification time). Values are shared between callers and must be treated as read-only.
"""

from collections import OrderedDict
import threading


class BoundedCache:
    """Least-recently-used mapping of at most `size` entries; `get` computes a missing value outside the lock."""

    def __init__(self, size):
        if size < 1:
            raise ValueError("cache size must be positive")
        self.size = size
        self._items = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key, compute):
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
                return self._items[key]
        # Slow work runs unlocked so one large parse never blocks other requests; two threads that miss the same
        # key both compute it and store equal values. A failing compute raises and stores nothing.
        value = compute()
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self.size:
                self._items.popitem(last=False)
        return value

    def __contains__(self, key):
        with self._lock:
            return key in self._items

    def __len__(self):
        with self._lock:
            return len(self._items)

    def clear(self):
        with self._lock:
            self._items.clear()
