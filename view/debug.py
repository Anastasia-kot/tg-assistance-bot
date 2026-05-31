from __future__ import annotations

from view.utils import format_execute_at

TELEGRAM_MESSAGE_LIMIT = 4096


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, bool) and not value:
        return True
    return False


def _format_field(name: str, value) -> str:
    if isinstance(value, bool):
        return f"{name}=true"
    formatted = format_execute_at(value)
    display = formatted if formatted else str(value)
    return f"{name}={display}"


def _format_task_row(
    task_id: int,
    text: str,
    created_at,
    execute_at,
    completed: bool,
    archived_at,
) -> list[str]:
    fields = (
        ("id", task_id),
        ("text", text),
        ("created_at", created_at),
        ("execute_at", execute_at),
        ("completed", completed),
        ("archived_at", archived_at),
    )
    return [
        _format_field(name, value)
        for name, value in fields
        if not _is_empty(value)
    ]


def _chunk_lines(lines: list[str], limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + (1 if current else 0)
        if current and current_len + line_len > limit:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line)
            continue
        current.append(line)
        current_len += line_len

    if current:
        chunks.append("\n".join(current))
    return chunks


class Debug:
    @staticmethod
    def get_all_tasks_lines(rows) -> list[str]:
        if not rows:
            return ["Таблица tasks пуста."]

        blocks = [
            _format_task_row(task_id, text, created_at, execute_at, completed, archived_at)
            for task_id, text, created_at, execute_at, completed, archived_at in rows
        ]
        lines = [f"Всего записей: {len(blocks)}", "───────────────"]
        for index, block in enumerate(blocks):
            if index > 0:
                lines.append("")
            lines.extend(block)
        return lines

    @staticmethod
    def print_all_tasks(bot, message, rows) -> None:
        for chunk in _chunk_lines(Debug.get_all_tasks_lines(rows)):
            bot.send_message(message.chat.id, text=chunk)


debug = Debug()
