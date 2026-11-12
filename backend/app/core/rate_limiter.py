"""Kullanıcı başına bellek içi kayan pencere.

Sayaç süreç içindedir; başka süreçlerle veya yeniden başlatmalarla paylaşılmaz.
"""

import threading
import time
from collections.abc import Callable


class RateLimiter:
    """60 saniyede 10 istek. Reddedilen istek pencereye yazılmaz."""

    def __init__(
        self,
        *,
        limit: int = 10,
        window_seconds: float = 60,
        clock: Callable[[], float] | None = None,
        counter: dict[str, list[float]] | None = None,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock or time.monotonic
        self._counter: dict[str, list[float]] = counter if counter is not None else {}
        self._lock = threading.Lock()

    def allow(self, user: str) -> tuple[bool, float]:
        """İstek sığıyorsa (True, 0), doluysa (False, retry_after_saniye) döner."""
        now = self._clock()
        with self._lock:
            kalan = [an for an in self._counter.get(user, []) if an > now - self._window]
            if len(kalan) >= self._limit:
                bekle = self._window - (now - kalan[0])
                self._counter[user] = kalan
                return False, max(bekle, 0.0)
            kalan.append(now)
            self._counter[user] = kalan
            return True, 0.0

    def blocked_for(self, user: str) -> tuple[bool, float]:
        """Limit doluysa (True, bekleme) döner. Sayaç artmaz."""
        now = self._clock()
        with self._lock:
            kalan = [an for an in self._counter.get(user, []) if an > now - self._window]
            self._counter[user] = kalan
            if len(kalan) >= self._limit:
                bekle = self._window - (now - kalan[0])
                return True, max(bekle, 0.0)
            return False, 0.0

    def reset(self) -> None:
        """Süreç içi sayacı temizler."""
        with self._lock:
            self._counter.clear()


limiter = RateLimiter()
login_failure_limiter = RateLimiter(limit=5)
