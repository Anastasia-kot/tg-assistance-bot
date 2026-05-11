from telebot import types

from auth import require_allowed_user
from view import print_list_tasks
from model import list_tasks

BTN_LIST_TASKS = "Список задач"


def build_main_reply_keyboard() -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(BTN_LIST_TASKS))
    return markup


def register_button_handlers(bot):

    @require_allowed_user(bot)
    def prompt_list_tasks(message):
        print_list_tasks(bot, message, list_tasks())

    @bot.message_handler(content_types=["text"])
    def buttons(message):
        if message.text == BTN_LIST_TASKS:
            prompt_list_tasks(message)
            return

        bot.send_message(
            message.chat.id,
            text="Я могу отвечать только на нажатие кнопок.",
        )
