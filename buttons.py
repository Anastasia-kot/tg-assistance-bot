from telebot import types

from auth import require_allowed_user
from view import print_list_tasks

from model import add_task, delete_tasks, get_id_by_index, list_tasks
from parsers import parse_add_command, parse_index_numbers


BTN_ADD_TASK = "Добавить задачу"
BTN_DELETE_TASK = "Удалить задачу"
BTN_LIST_TASKS = "Список задач"


def build_main_reply_keyboard() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton(BTN_ADD_TASK),
        types.KeyboardButton(BTN_DELETE_TASK),
        types.KeyboardButton(BTN_LIST_TASKS),
    )
    return markup

def register_button_handlers(bot):
    @require_allowed_user(bot)
    def handle_add_step(next_message):
        task_text, task_date = parse_add_command(f"/add {next_message.text or ''}")
        if not task_text:
            bot.send_message(next_message.chat.id, text="Пустой текст задачи.")
            return
        add_task(task_text, task_date)
        bot.send_message(next_message.chat.id, text="Задача добавлена.")
        print_list_tasks(bot, next_message, list_tasks())

    @require_allowed_user(bot)
    def handle_delete_step(next_message):
        raw = (next_message.text or "").strip()
        indices = parse_index_numbers(raw)
        if not indices:
            bot.send_message(next_message.chat.id, text="Укажи номера задач цифрами.")
            return
        try:
            task_ids = [get_id_by_index(i) for i in indices]
        except ValueError as exc:
            bot.send_message(next_message.chat.id, text=str(exc))
            return
        delete_tasks(task_ids)
        bot.send_message(next_message.chat.id, text="Задачи удалены.")
        print_list_tasks(bot, next_message, list_tasks())

    @require_allowed_user(bot)
    def prompt_add_task(message):
        bot.send_message(
            message.chat.id,
            text="Ок. Напиши задачу текстом следующим сообщением "
            "(или «текст execute_at дата»).",
        )
        bot.register_next_step_handler(message, handle_add_step)

    @require_allowed_user(bot)
    def prompt_delete_task(message):
        bot.send_message(
            message.chat.id,
            text="Ок. Напиши номера задач для удаления (как в списке).",
        )
        bot.register_next_step_handler(message, handle_delete_step)

    @require_allowed_user(bot)
    def prompt_list_tasks(message):
        print_list_tasks(bot, message, list_tasks())

    @bot.message_handler(content_types=["text"])
    def buttons(message):
        if message.text == BTN_ADD_TASK:
            prompt_add_task(message)
            return

        if message.text == BTN_DELETE_TASK:
            prompt_delete_task(message)
            return

        if message.text == BTN_LIST_TASKS:
            prompt_list_tasks(message)
            return

        bot.send_message(
            message.chat.id,
            text="Я могу отвечать только на нажатие кнопок",
        )
