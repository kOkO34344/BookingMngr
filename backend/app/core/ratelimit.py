"""A small in-process rate limiter for the login endpoint.

Deliberately not Redis-backed: there is one backend container, so per-process
state is the whole picture. If the deployment ever grows a second replica this
becomes per-replica and the limit effectively multiplies — that is the point at
which it should move to a shared store.

Only *failed* attempts are counted, so somebody using the app normally can
never trip it.
"""

from __future__ import annotations

import time
from collections import defaultdict


class AttemptLimiter:
    def __init__(self, *, max_attempts: int = 10, window_seconds: int = 900) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str, now: float) -> list[float]:
        cutoff = now - self.window_seconds
        recent = [stamp for stamp in self._failures[key] if stamp > cutoff]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def retry_after(self, key: str) -> int | None:
        """Seconds the caller must wait, or None if they may try now."""
        now = time.monotonic()
        recent = self._prune(key, now)
        if len(recent) < self.max_attempts:
            return None
        # The window slides, so the block lifts when the oldest failure ages out.
        return max(1, int(self.window_seconds - (now - recent[0])))

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        self._prune(key, now)
        self._failures[key].append(now)

    def reset(self, key: str) -> None:
        """Clear on success so a correct password immediately unblocks."""
        self._failures.pop(key, None)


#: Shared by the login endpoint. Ten wrong passwords per quarter-hour, per
#: (client IP, username) pair.
login_limiter = AttemptLimiter()
