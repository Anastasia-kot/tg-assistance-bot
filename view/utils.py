from __future__ import annotations

import uuid
from datetime import datetime


def display_indices_for_task_db_ids(
    rows: list[tuple[int, str, bool, object]],
    task_db_ids: frozenset[int] | set[int],
) -> list[int]:
    """Номера строк списка (1-based), как в get_list_tasks, для заданных id задач в БД."""
    wanted = {int(x) for x in task_db_ids}
    return [
        display_idx
        for display_idx, (tid, _t, _d, _e) in enumerate(rows, start=1)
        if int(tid) in wanted
    ]


def new_token() -> str:
    """Короткий токен для callback_data (лимит Telegram на кнопку)."""
    return uuid.uuid4().hex[:12]


def format_execute_at(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    return str(value)
