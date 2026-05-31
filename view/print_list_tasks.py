from view.get_list_tasks import (
    get_list_tasks,
    get_list_tasks_html_complete_mark,
    get_list_tasks_html_strike,
)


def print_list_tasks(bot, message, rows, title: str | None = None) -> None:
    lines = get_list_tasks(rows)
    text = "\n".join(lines)
    if title:
        text = f"{title}\n\n{text}"
    bot.send_message(message.chat.id, text=text)


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
