import time
from collections import defaultdict
from threading import Lock

WINDOW_SECONDS = 300
MAX_ATTEMPTS = 5

_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def is_locked(key: str) -> bool:
    with _lock:
        now = time.time()
        _attempts[key] = [t for t in _attempts[key] if now - t < WINDOW_SECONDS]
        return len(_attempts[key]) >= MAX_ATTEMPTS


def register_failure(key: str) -> None:
    with _lock:
        _attempts[key].append(time.time())


def reset(key: str) -> None:
    with _lock:
        _attempts.pop(key, None)
