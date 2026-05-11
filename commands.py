from auth import require_allowed_user
from ai import get_ai_response
from database import add_task, complete_tasks, delete_tasks, get_id_by_index, list_tasks
from parsers import parse_add_command, parse_index_numbers
from ui import print_list_tasks


def register_command_handlers(bot):
    @bot.message_handler(commands=["start"])
    def start_message(message):
        bot.send_message(
            message.chat.id,
            text="Привет, {0.first_name} \nТест 5".format(
                message.from_user
            ),
            # добавление кнопок
            # reply_markup=build_main_reply_keyboard(),
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

        bot.send_message(message.chat.id, text=answer)