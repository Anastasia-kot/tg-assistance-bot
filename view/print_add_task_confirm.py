from telebot import types

from model.temporary import set_pending_task
from view.utils import new_token


CB_ADD_TASK_YES_PREFIX = "add_task:yes:"
CB_ADD_TASK_NO_PREFIX = "add_task:no:"


def print_add_task(bot, message, task: dict) -> None:
    description = (task or {}).get("description", "")
    execute_at = (task or {}).get("time", "")

    token = new_token()
    set_pending_task(token, {"description": description, "time": execute_at})

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
