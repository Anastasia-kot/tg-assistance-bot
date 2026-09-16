from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PendingStory:
    file_id: str
    caption: Optional[str] = None
    is_waiting_for_caption: bool = False


_lock = threading.Lock()
_pending: dict[int, PendingStory] = {}


def set_pending(telegram_id: int, file_id: str) -> None:
    with _lock:
        _pending[int(telegram_id)] = PendingStory(file_id=file_id)


def get_pending(telegram_id: int) -> Optional[PendingStory]:
    with _lock:
        return _pending.get(int(telegram_id))


def wait_for_caption(telegram_id: int) -> Optional[PendingStory]:
    with _lock:
        story = _pending.get(int(telegram_id))
        if story is None:
            return None
        updated = PendingStory(
            file_id=story.file_id,
            caption=story.caption,
            is_waiting_for_caption=True,
        )
        _pending[int(telegram_id)] = updated
        return updated


def set_caption(telegram_id: int, caption: str) -> Optional[PendingStory]:
    with _lock:
        story = _pending.get(int(telegram_id))
        if story is None or not story.is_waiting_for_caption:
            return None
        updated = PendingStory(file_id=story.file_id, caption=caption)
        _pending[int(telegram_id)] = updated
        return updated


def is_waiting_for_caption(telegram_id: int) -> bool:
    with _lock:
        story = _pending.get(int(telegram_id))
        return bool(story and story.is_waiting_for_caption)


def pop_pending(telegram_id: int) -> Optional[PendingStory]:
    with _lock:
        return _pending.pop(int(telegram_id), None)


def clear_pending(telegram_id: int) -> None:
    pop_pending(telegram_id)
