from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from threading import Lock


class FixedWindowRateLimiter:
    """Small per-process abuse guard; it never stores business memory."""

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        max_keys: int = 2_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1 or window_seconds <= 0 or max_keys < 1:
            raise ValueError("rate limit and window must be positive")
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._buckets: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = self._clock()
        cutoff = now - self._window
        with self._lock:
            if len(self._buckets) >= self._max_keys and key not in self._buckets:
                expired = [
                    bucket_key
                    for bucket_key, values in self._buckets.items()
                    if not values or values[-1] <= cutoff
                ]
                for bucket_key in expired:
                    self._buckets.pop(bucket_key, None)
                if len(self._buckets) >= self._max_keys:
                    oldest_key = min(self._buckets, key=lambda item: self._buckets[item][-1])
                    self._buckets.pop(oldest_key, None)
            bucket = self._buckets.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._limit:
                retry_after = max(1, int(self._window - (now - bucket[0])) + 1)
                return False, retry_after
            bucket.append(now)
            return True, 0
