from __future__ import annotations

from view.utils import format_execute_at

TELEGRAM_MESSAGE_LIMIT = 4096


def _format_db_value(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    formatted = format_execute_at(value)
    return formatted if formatted else str(value)


def _format_task_row(
    task_id: int,
    text: str,
    created_at,
    execute_at,
    completed: bool,
    archived_at,
) -> str:
    return (
        f"id={task_id}\n"
        f"text={text}\n"
        f"created_at={_format_db_value(created_at)}\n"
        f"execute_at={_format_db_value(execute_at)}\n"
        f"completed={_format_db_value(completed)}\n"
        f"archived_at={_format_db_value(archived_at)}"
    )


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
        return [f"Всего записей: {len(blocks)}", "───────────────", *blocks]

    @staticmethod
    def print_all_tasks(bot, message, rows) -> None:
        for chunk in _chunk_lines(Debug.get_all_tasks_lines(rows)):
            bot.send_message(message.chat.id, text=chunk)


debug = Debug()
