from __future__ import annotations

import json

from auth import require_allowed_user
from model import get_id_by_index, list_tasks

from .ai import get_ai_response
from view import (
    print_add_task,
    print_complete_tasks_confirm,
    print_delete_tasks_confirm,
    print_list_tasks,
)

_AI_EMPTY_IDS_HINT = "Не указаны номера задач."


def _queue_task_ids_from_ai_payload(
    bot,
    message,
    payload: dict,
    apply_by_task_ids,
) -> None:
    indices = payload.get("ids")
    if not indices:
        bot.send_message(message.chat.id, text=_AI_EMPTY_IDS_HINT)
        return
    try:
        task_ids = [get_id_by_index(i) for i in indices]
    except ValueError as exc:
        bot.send_message(message.chat.id, text=str(exc))
        return
    rows = list_tasks()
    apply_by_task_ids(bot, message, task_ids, rows)


def register_command_handlers(bot):
    @bot.message_handler(func=lambda m: isinstance(m.text, str))
    @require_allowed_user(bot)
    def ai_message(message):

        try:
            answer = get_ai_response(message.text)
        except Exception as exc:
            return bot.send_message(message.chat.id, text=f"Ошибка AI: {exc}")

        try:
            payload = json.loads(answer)
        except json.JSONDecodeError:
            return bot.send_message(message.chat.id, text=answer)

        if not isinstance(payload, dict):
            return bot.send_message(message.chat.id, text=answer)

        action = payload.get("type")

        if action == "/list":
            return print_list_tasks(bot, message, list_tasks())

        if action == "/delete":
            return _queue_task_ids_from_ai_payload(
                bot, message, payload, print_delete_tasks_confirm
            )

        if action == "/complete":
            return _queue_task_ids_from_ai_payload(
                bot, message, payload, print_complete_tasks_confirm
            )

        if action == "/add":
            return print_add_task(bot, message, payload)

