import logging

from model.tasks import select_today_tasks, select_tomorrow_tasks
from view.print_list_tasks import print_list_tasks


logger = logging.getLogger("notifications")

_notification_chat_id: int | None = None
_bot = None


def set_notification_chat_id(chat_id: int) -> None:
    global _notification_chat_id
    _notification_chat_id = int(chat_id)


def set_notifications_bot(bot) -> None:
    global _bot
    _bot = bot


class _ChatWrapper:
    def __init__(self, chat_id: str | int) -> None:
        self.id = int(chat_id)


class _MessageWrapper:
    def __init__(self, chat_id: str | int) -> None:
        self.chat = _ChatWrapper(chat_id)


def notify_tomorrow_tasks() -> None:
    if _bot is None or _notification_chat_id is None:
        logger.warning(
            "notify_tomorrow_tasks: bot or notification chat id is not set yet",
        )
        return

    tasks = select_tomorrow_tasks()
    if not tasks:
        return

    message = _MessageWrapper(_notification_chat_id)
    print_list_tasks(_bot, message, tasks, title="Задачи на завтра:")


def notify_today_tasks() -> None:
    if _bot is None or _notification_chat_id is None:
        logger.warning(
            "notify_today_tasks: bot or notification chat id is not set yet",
        )
        return

    tasks = select_today_tasks()
    if not tasks:
        return

    _bot.send_message(chat_id=_notification_chat_id, text="Задачи на сегодня:")
    message = _MessageWrapper(_notification_chat_id)
    print_list_tasks(_bot, message, tasks)
