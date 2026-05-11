from __future__ import annotations

import html
import re

from view.utils import format_execute_at

DONE_MARK = "✅"
PENDING_DONE_MARK = "☑"
BLOCK_SEP = "───────────────"

_TASK_LINE_PREFIX = re.compile(r"^(\d+)\.")


def get_list_tasks(rows) -> list[str]:
    if not rows:
        return ["Список задач пуст."]

    lines: list[str] = []
    pending_block_started = False
    for idx, (_, text, is_completed, execute_at) in enumerate(rows, start=1):
        if not is_completed and not pending_block_started:
            pending_block_started = True
            if lines:
                lines.append(BLOCK_SEP)
        due = format_execute_at(execute_at)
        due_part = f" ({due})" if due else ""
        lines.append(f"{idx}. {text}{due_part}" + (f" {DONE_MARK}" if is_completed else ""))

    return lines


def get_list_tasks_html_strike(
    lines: list[str], ids: list[int]
) -> list[str]:
    """Берёт готовые строки от get_list_tasks и оборачивает в <s> строки с номерами из списка (1-based)."""
    strike = frozenset(int(x) for x in ids)
    out: list[str] = []
    for line in lines:
        match = _TASK_LINE_PREFIX.match(line)
        if match:
            idx = int(match.group(1))
            escaped = html.escape(line)
            out.append(f"<s>{escaped}</s>" if idx in strike else escaped)
        else:
            out.append(html.escape(line))
    return out


def get_list_tasks_html_complete_mark(
    lines: list[str], ids: list[int]
) -> list[str]:
    """Строки от get_list_tasks: к отмеченным номерам добавляется ☑, если задача ещё без ✅."""
    mark = frozenset(int(x) for x in ids)
    out: list[str] = []
    for line in lines:
        match = _TASK_LINE_PREFIX.match(line)
        if match:
            idx = int(match.group(1))
            escaped = html.escape(line)
            if idx in mark:
                if line.endswith(f" {DONE_MARK}"):
                    out.append(escaped)
                else:
                    out.append(f"{escaped} {PENDING_DONE_MARK}")
            else:
                out.append(escaped)
        else:
            out.append(html.escape(line))
    return out
