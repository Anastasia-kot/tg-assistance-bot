from telebot import types

from auth import require_allowed_user
from view import print_list_tasks
from model import list_tasks, list_tomorrow_tasks

BTN_LIST_TASKS = "Список задач"
BTN_LIST_TOMORROW_TASKS = "Список задач на завтра"

_REPLY_KEYBOARD_BUTTONS = frozenset({BTN_LIST_TASKS, BTN_LIST_TOMORROW_TASKS})


def build_main_reply_keyboard() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(BTN_LIST_TASKS))
    markup.add(types.KeyboardButton(BTN_LIST_TOMORROW_TASKS))
    return markup


def register_button_handlers(bot):

    @require_allowed_user(bot)
    def prompt_list_tasks(message):
        print_list_tasks(bot, message, list_tasks())

    @require_allowed_user(bot)
    def prompt_list_tomorrow_tasks(message):
        rows = list_tomorrow_tasks()
        if not rows:
            bot.send_message(message.chat.id, text="Задач на завтра нет.")
            return
        bot.send_message(message.chat.id, text="Задачи на завтра:")
        print_list_tasks(bot, message, rows)

    @bot.message_handler(func=lambda message: message.text == BTN_LIST_TASKS)
    @require_allowed_user(bot)
    def list_tasks_button(message):
        prompt_list_tasks(message)

    @bot.message_handler(func=lambda message: message.text == BTN_LIST_TOMORROW_TASKS)
    @require_allowed_user(bot)
    def list_tomorrow_tasks_button(message):
        prompt_list_tomorrow_tasks(message)
