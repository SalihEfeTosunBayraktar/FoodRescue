from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Callable


class FailureLimiter:
    """Sliding-window failure counter. A key is locked while it has `max_failures` recent failures."""

    def __init__(self, max_failures: int, window_seconds: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str) -> deque[float]:
        events = self._failures[key]
        cutoff = self._clock() - self._window
        while events and events[0] <= cutoff:
            events.popleft()
        return events

    def retry_after(self, key: str) -> int:
        """Seconds until the key is unlocked; 0 when not locked."""
        with self._lock:
            events = self._prune(key)
            if len(events) < self._max:
                return 0
            return max(1, int(events[0] + self._window - self._clock()) + 1)

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._prune(key).append(self._clock())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
