import json

from auth import require_allowed_user
from model import add_task, complete_tasks, delete_tasks, get_id_by_index, list_tasks

from .ai import get_ai_response
from .buttons import build_main_reply_keyboard
from .parsers import parse_add_command, parse_index_numbers
from view import (
    CB_ADD_TASK_NO_PREFIX,
    CB_ADD_TASK_YES_PREFIX,
    pop_pending_add_task,
    print_add_task,
    print_list_tasks,
)

from version import VERSION


def register_command_handlers(bot):
    @bot.message_handler(commands=["start"])
    def start_message(message):
        bot.send_message(
            message.chat.id,
            text=f"Привет, {message.from_user.first_name} \nВерсия {VERSION}",
            # добавление кнопок
            reply_markup=build_main_reply_keyboard(),
        )

    @bot.message_handler(
        func=lambda m: isinstance(m.text, str) and m.text.startswith("/list")
    )
    @require_allowed_user(bot)
    def list_tasks_message(message):
        print_list_tasks(bot, message, list_tasks())

    @bot.message_handler(
        func=lambda m: isinstance(m.text, str) and m.text.startswith("/add")
    )
    @require_allowed_user(bot)
    def add_task_message(message):
        task_text, task_date = parse_add_command(message.text)
        if not task_text:
            bot.send_message(
                message.chat.id,
                text="Используй: /add <текст задачи> или /add текст execute_at <дата>",
            )
            return

        add_task(task_text, task_date)
        bot.send_message(message.chat.id, text=f"Добавлена задача: {task_text}.")
        print_list_tasks(bot, message, list_tasks())

    @bot.message_handler(
        func=lambda m: isinstance(m.text, str) and m.text.startswith("/delete")
    )
    @require_allowed_user(bot)
    def delete_task_message(message):
        raw = message.text[len("/delete") :].strip()
        indices = parse_index_numbers(raw)
        if not indices:
            bot.send_message(message.chat.id, text="Используй: /delete <номера задач>")
            return

        try:
            task_ids = [get_id_by_index(i) for i in indices]
        except ValueError as exc:
            bot.send_message(message.chat.id, text=str(exc))
            return

        delete_tasks(task_ids)
        print_list_tasks(bot, message, list_tasks())

    @bot.message_handler(
        func=lambda m: isinstance(m.text, str) and m.text.startswith("/complete")
    )
    @require_allowed_user(bot)
    def complete_task_message(message):
        raw = message.text[len("/complete") :].strip()
        indices = parse_index_numbers(raw)
        if not indices:
            bot.send_message(message.chat.id, text="Используй: /complete <номера задач>")
            return

        try:
            task_ids = [get_id_by_index(i) for i in indices]
        except ValueError as exc:
            bot.send_message(message.chat.id, text=str(exc))
            return

        complete_tasks(task_ids)
        print_list_tasks(bot, message, list_tasks())

    @bot.message_handler(func=lambda m: isinstance(m.text, str))
    @require_allowed_user(bot)
    def ai_message(message):

        try:
            answer = get_ai_response(message.text)
        except Exception as exc:
            bot.send_message(message.chat.id, text=f"Ошибка AI: {exc}")
            return

        try:
            payload = json.loads(answer)
        except json.JSONDecodeError:
            bot.send_message(message.chat.id, text=answer)
            return

        if not isinstance(payload, dict):
            bot.send_message(message.chat.id, text=answer)
            return

        print_add_task(bot, message, payload)

    @bot.callback_query_handler(
        func=lambda c: isinstance(c.data, str)
        and c.data.startswith(CB_ADD_TASK_YES_PREFIX)
    )
    def add_task_confirm(call):
        token = call.data[len(CB_ADD_TASK_YES_PREFIX) :]
        pending = pop_pending_add_task(token)
        if not pending:
            bot.answer_callback_query(call.id, text="Запрос устарел")
            return

        add_task(pending["description"], pending["time"] or None)
        bot.answer_callback_query(call.id, text="Добавлено")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Добавлена задача: {pending['description']}.",
        )
        print_list_tasks(bot, call.message, list_tasks())

    @bot.callback_query_handler(
        func=lambda c: isinstance(c.data, str)
        and c.data.startswith(CB_ADD_TASK_NO_PREFIX)
    )
    def add_task_cancel(call):
        token = call.data[len(CB_ADD_TASK_NO_PREFIX) :]
        pop_pending_add_task(token)
        bot.answer_callback_query(call.id, text="Отменено")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Добавление задачи отменено.",
        )