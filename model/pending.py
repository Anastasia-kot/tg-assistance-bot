from __future__ import annotations

import threading
from typing import Optional

_lock = threading.Lock()
_pending: dict[int, str] = {}


def set_pending(telegram_id: int, file_id: str) -> None:
    with _lock:
        _pending[int(telegram_id)] = file_id


def get_pending(telegram_id: int) -> Optional[str]:
    with _lock:
        return _pending.get(int(telegram_id))


def pop_pending(telegram_id: int) -> Optional[str]:
    with _lock:
        return _pending.pop(int(telegram_id), None)


def clear_pending(telegram_id: int) -> None:
    pop_pending(telegram_id)
