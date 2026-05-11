import uuid
from datetime import datetime

from telebot import types


def _format_execute_at(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    return str(value)


def print_list_tasks(bot, message, rows) -> None:
    if not rows:
        bot.send_message(message.chat.id, text="Список задач пуст.")
        return

    done_mark = "✅"
    block_sep = "───────────────"
    lines: list[str] = []
    pending_block_started = False
    for idx, (_, text, is_completed, execute_at) in enumerate(rows, start=1):
        if not is_completed and not pending_block_started:
            pending_block_started = True
            if lines:
                lines.append(block_sep)
        due = _format_execute_at(execute_at)
        due_part = f" ({due})" if due else ""
        lines.append(f"{idx}. {text}{due_part}" + (f" {done_mark}" if is_completed else ""))

    bot.send_message(message.chat.id, text="\n".join(lines))


CB_ADD_TASK_YES_PREFIX = "add_task:yes:"
CB_ADD_TASK_NO_PREFIX = "add_task:no:"

_pending_add_tasks: dict[str, dict] = {}

def pop_pending_add_task(token: str) -> dict | None:
    return _pending_add_tasks.pop(token, None)

def print_add_task(bot, message, task: dict) -> None:
    description = (task or {}).get("description", "")
    execute_at = (task or {}).get("time", "")

    token = uuid.uuid4().hex[:12]
    _pending_add_tasks[token] = {
        "description": description,
        "time": execute_at,
    }

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton(
            "Да", callback_data=f"{CB_ADD_TASK_YES_PREFIX}{token}"
        ),
        types.InlineKeyboardButton(
            "Нет", callback_data=f"{CB_ADD_TASK_NO_PREFIX}{token}"
        ),
    )

    text = f"Добавить новую задачу «{description}» со сроком {execute_at}?"
    bot.send_message(message.chat.id, text=text, reply_markup=markup)
