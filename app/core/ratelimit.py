from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Callable


# Kayan pencere (sliding window) ile hatalı deneme sayacı. Her anahtar (e-posta, işletme no) için
# hata zamanlarını tutar, pencereden eski olanları atar. Pencerede `max_failures` hata varsa anahtar
# kilitlidir.
class FailureLimiter:
    """Sliding-window failure counter. A key is locked while it has `max_failures` recent failures."""

    # `clock` parametresi bağımlılık enjeksiyonudur: testte sahte bir saat verip beklemeden zamanı
    # ilerletebiliriz. time.monotonic sistem saati değişse bile geri gitmez.
    def __init__(self, max_failures: int, window_seconds: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        # deque: iki ucundan hızlı ekleme/çıkarma sağlar; en eski hata başta, en yeni sonda durur.
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        # FastAPI senkron endpoint'leri thread havuzunda çalışır: aynı sayaca aynı anda birden çok
        # thread erişebilir. Kilit (lock) sayacın bozulmasını önler.
        self._lock = threading.Lock()

    # Pencerenin dışına düşmüş (eski) hataları baştan temizler.
    def _prune(self, key: str) -> deque[float]:
        events = self._failures[key]
        cutoff = self._clock() - self._window
        while events and events[0] <= cutoff:
            events.popleft()
        return events

    # Kilitliyse kaç saniye sonra açılacağını verir, değilse 0. En eski hata pencereden çıkınca bir
    # yer açılır.
    def retry_after(self, key: str) -> int:
        """Seconds until the key is unlocked; 0 when not locked."""
        with self._lock:
            events = self._prune(key)
            if len(events) < self._max:
                return 0
            return max(1, int(events[0] + self._window - self._clock()) + 1)

    # Başarısız bir denemeyi kaydeder.
    def record_failure(self, key: str) -> None:
        with self._lock:
            self._prune(key).append(self._clock())

    # Başarılı denemeden sonra sayaç sıfırlanır: doğru parolayı giren kullanıcı cezalandırılmaz.
    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
