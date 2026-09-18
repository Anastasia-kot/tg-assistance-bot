from __future__ import annotations

import threading
from contextlib import contextmanager

_locks_guard = threading.Lock()
_user_locks: dict[int, threading.Lock] = {}


def _lock_for(telegram_id: int) -> threading.Lock:
    with _locks_guard:
        lock = _user_locks.get(telegram_id)
        if lock is None:
            lock = threading.Lock()
            _user_locks[telegram_id] = lock
        return lock


@contextmanager
def user_lock(telegram_id: int):
    lock = _lock_for(telegram_id)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()
