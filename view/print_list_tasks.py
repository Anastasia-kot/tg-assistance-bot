from view.get_list_tasks import (
    get_list_tasks,
    get_list_tasks_html_complete_mark,
    get_list_tasks_html_strike,
)


def print_list_tasks(bot, message, rows) -> None:
    bot.send_message(message.chat.id, text="\n".join(get_list_tasks(rows)))


def print_list_tasks_with_delete(bot, message, rows, ids: list[int]) -> None:
    lines = get_list_tasks_html_strike(get_list_tasks(rows), ids)
    bot.send_message(
        message.chat.id,
        text="\n".join(lines),
        parse_mode="HTML",
    )


def print_list_tasks_with_complete(bot, message, rows, ids: list[int]) -> None:
    lines = get_list_tasks_html_complete_mark(get_list_tasks(rows), ids)
    bot.send_message(
        message.chat.id,
        text="\n".join(lines),
        parse_mode="HTML",
    )
