from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PendingStory:
    file_id: str
    caption: Optional[str] = None
    is_waiting_for_caption: bool = False
    published_targets: frozenset[str] = frozenset()


_lock = threading.Lock()
_pending: dict[int, PendingStory] = {}


def set_pending(
    telegram_id: int,
    file_id: str,
    caption: Optional[str] = None,
) -> None:
    with _lock:
        _pending[int(telegram_id)] = PendingStory(
            file_id=file_id,
            caption=caption,
        )


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
            published_targets=story.published_targets,
        )
        _pending[int(telegram_id)] = updated
        return updated


def set_caption(telegram_id: int, caption: str) -> Optional[PendingStory]:
    with _lock:
        story = _pending.get(int(telegram_id))
        if story is None or not story.is_waiting_for_caption:
            return None
        updated = PendingStory(
            file_id=story.file_id,
            caption=caption,
            published_targets=story.published_targets,
        )
        _pending[int(telegram_id)] = updated
        return updated


def remove_caption(telegram_id: int) -> Optional[PendingStory]:
    with _lock:
        story = _pending.get(int(telegram_id))
        if story is None:
            return None
        updated = PendingStory(
            file_id=story.file_id,
            published_targets=story.published_targets,
        )
        _pending[int(telegram_id)] = updated
        return updated


def is_waiting_for_caption(telegram_id: int) -> bool:
    with _lock:
        story = _pending.get(int(telegram_id))
        return bool(story and story.is_waiting_for_caption)


def mark_target_published(
    telegram_id: int,
    target: str,
) -> Optional[PendingStory]:
    with _lock:
        story = _pending.get(int(telegram_id))
        if story is None:
            return None
        updated = PendingStory(
            file_id=story.file_id,
            caption=story.caption,
            published_targets=story.published_targets | {target},
        )
        _pending[int(telegram_id)] = updated
        return updated


def pop_pending(telegram_id: int) -> Optional[PendingStory]:
    with _lock:
        return _pending.pop(int(telegram_id), None)


def clear_pending(telegram_id: int) -> None:
    pop_pending(telegram_id)
