from __future__ import annotations

import threading


_lock = threading.Lock()
_waiting: set[int] = set()


def begin_vk_login(telegram_id: int) -> None:
    with _lock:
        _waiting.add(int(telegram_id))


def is_waiting_vk_token(telegram_id: int) -> bool:
    with _lock:
        return int(telegram_id) in _waiting


def clear_vk_login(telegram_id: int) -> None:
    with _lock:
        _waiting.discard(int(telegram_id))
