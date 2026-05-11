import html

from telebot import types

from model.temporary import set_pending_task
from view.get_list_tasks import get_list_tasks, get_list_tasks_html_strike
from view.utils import display_indices_for_task_db_ids, new_token

CB_BULK_DELETE_YES_PREFIX = "delete_tasks:yes"
CB_BULK_DELETE_NO_PREFIX = "delete_tasks:no"

TITLE = "Удалить отмеченные задачи?"
LEGEND = "\n\n<i>Зачёркнутые строки будут удалены.</i>"


def print_delete_tasks_confirm(
    bot, message, task_ids: list[int], rows: list[tuple[int, str, bool, object]]
) -> None:
    token = new_token()
    id_set = frozenset(int(x) for x in task_ids)
    set_pending_task(token, {"action": "delete", "task_ids": list(id_set)})

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton(
            "Да", callback_data=f"{CB_BULK_DELETE_YES_PREFIX}{token}"
        ),
        types.InlineKeyboardButton(
            "Нет", callback_data=f"{CB_BULK_DELETE_NO_PREFIX}{token}"
        ),
    )

    plain = get_list_tasks(rows)
    display_nums = display_indices_for_task_db_ids(rows, id_set)
    preview_lines = get_list_tasks_html_strike(plain, display_nums)
    preview = "\n".join(preview_lines)

    text = f"<b>{html.escape(TITLE)}</b>\n\n{preview}{LEGEND}"
    bot.send_message(message.chat.id, text=text, parse_mode="HTML", reply_markup=markup)
