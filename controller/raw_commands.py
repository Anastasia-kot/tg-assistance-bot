from __future__ import annotations

from collections.abc import Callable
import logging

from telebot.util import extract_arguments

from auth import is_allowed_user, require_allowed_user
from model import add_task, complete_tasks, delete_tasks, get_id_by_index, list_tasks

from .buttons import BTN_LIST_TASKS, build_main_reply_keyboard
from .parsers import parse_add_command, parse_index_numbers
from view import print_list_tasks

from version import VERSION

logger = logging.getLogger(__name__)


def _run_bulk_task_action_by_display_indices(
    bot,
    message,
    *,
    usage_hint: str,
    apply_by_task_ids: Callable[[list[int]], None],
) -> None:
    raw = (extract_arguments(message.text) or "").strip()
    indexes = parse_index_numbers(raw)
    if not indexes:
        bot.send_message(message.chat.id, text=usage_hint)
        return
    try:
        task_ids = [get_id_by_index(i) for i in indexes]
    except ValueError as exc:
        bot.send_message(message.chat.id, text=str(exc))
        return
    apply_by_task_ids(task_ids)
    print_list_tasks(bot, message, list_tasks())


def raw_command_handlers(bot):
    # /start
    @bot.message_handler(commands=["start"])
    def start_message(message):
        user = getattr(message, "from_user", None)
        user_payload = getattr(user, "__dict__", None) if user is not None else None
        logger.info("start command from user: %r", user_payload)
        start_hint = (
            f"👋 Привет, {message.from_user.first_name}!\n"
            f"📦 Версия приложения: {VERSION}\n"
            "\n"
            f"📋 Кнопка «{BTN_LIST_TASKS}» — выведет список задач.\n"
            "\n"
            "➕ Добавление задачи:\n"
            "   • голосовым вводом\n"
            "   • или текстом в чат в свободной форме\n"
            "\n"
            "🗑 Удаление задачи:\n"
            "   • голосовым вводом\n"
            "   • или текстом в чат номера из списка задач\n"
            "\n"
            "✅ Отметка выполненными:\n"
            "   • голосовым вводом\n"
            "   • или текстом в чат номера из списка задач"
        )
        bot.send_message(
            message.chat.id,
            text=start_hint,
            reply_markup=build_main_reply_keyboard(),
        )
        if is_allowed_user(message):
            from model.notifications import set_notification_chat_id

            set_notification_chat_id(message.chat.id)

    # /list
    @bot.message_handler(commands=["list"])
    @require_allowed_user(bot)
    def list_tasks_message(message):
        print_list_tasks(bot, message, list_tasks())

    # /add
    @bot.message_handler(commands=["add"])
    @require_allowed_user(bot)
    def add_task_message(message):
        task_text, task_date = parse_add_command(message.text)
        if not task_text:
            return bot.send_message(
                message.chat.id,
                text="Используй: /add <текст задачи> или /add текст execute_at <дата>",
            )
        add_task(task_text, task_date)
        bot.send_message(message.chat.id, text=f"Добавлена задача: {task_text}.")
        print_list_tasks(bot, message, list_tasks())

    # /delete
    @bot.message_handler(commands=["delete"])
    @require_allowed_user(bot)
    def delete_task_message(message):
        _run_bulk_task_action_by_display_indices(
            bot,
            message,
            usage_hint="Используй: /delete <номера задач>",
            apply_by_task_ids=delete_tasks,
        )

    # /complete
    @bot.message_handler(commands=["complete"])
    @require_allowed_user(bot)
    def complete_task_message(message):
        _run_bulk_task_action_by_display_indices(
            bot,
            message,
            usage_hint="Используй: /complete <номера задач>",
            apply_by_task_ids=complete_tasks,
        )
