import re

from telebot import types

from auth import is_allowed_user
from database import add_task, complete_tasks, delete_tasks, get_id_by_index, list_tasks


def parse_add_command(text: str) -> tuple[str, str | None]:
    payload = text[len("/add") :].strip()
    marker = "execute_at"
    if marker in payload:
        left, _, right = payload.partition(marker)
        task_text = left.strip()
        task_date = right.strip() or None
        return task_text, task_date
    return payload, None


def parse_index_numbers(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]


def print_list_tasks(bot, message):
    rows = list_tasks()
    if not rows:
        bot.send_message(message.chat.id, text="Список задач пуст.")
        return

    lines = [f"{idx}. {text}" for idx, (_, text) in enumerate(rows, start=1)]
    bot.send_message(message.chat.id, text="\n".join(lines))


def register_command_handlers(bot):
    def require_allowed_user(handler):
        def wrapped(message):
            if not is_allowed_user(message):
                bot.send_message(message.chat.id, text="Нет доступа.")
                return
            return handler(message)

        return wrapped

    @bot.message_handler(commands=["start"])
    @require_allowed_user
    def start_message(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard_buttons = [
            types.KeyboardButton("Добавить задачу"),
            types.KeyboardButton("Удалить задачу"),
            types.KeyboardButton("Список задач"),
        ]
        markup.add(*keyboard_buttons)

        bot.send_message(
            message.chat.id,
            text="Привет, {0.first_name} \n👇 Воспользуйся кнопками".format(
                message.from_user
            ),
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m: isinstance(m.text, str) and m.text.startswith("/list")
    )
    @require_allowed_user
    def list_tasks_message(message):
        print_list_tasks(bot, message)

    @bot.message_handler(
        func=lambda m: isinstance(m.text, str) and m.text.startswith("/add")
    )
    @require_allowed_user
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
        print_list_tasks(bot, message)

    @bot.message_handler(
        func=lambda m: isinstance(m.text, str) and m.text.startswith("/delete")
    )
    @require_allowed_user
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
        print_list_tasks(bot, message)

    @bot.message_handler(
        func=lambda m: isinstance(m.text, str) and m.text.startswith("/complete")
    )
    @require_allowed_user
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
        print_list_tasks(bot, message)
