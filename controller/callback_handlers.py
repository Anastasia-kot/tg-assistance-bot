from auth import require_allowed_user
from model import add_task, complete_tasks, delete_tasks, list_tasks
from model.temporary import pop_pending_task
from view import (
    CB_ADD_TASK_NO_PREFIX,
    CB_ADD_TASK_YES_PREFIX,
    CB_BULK_COMPLETE_NO_PREFIX,
    CB_BULK_COMPLETE_YES_PREFIX,
    CB_BULK_DELETE_NO_PREFIX,
    CB_BULK_DELETE_YES_PREFIX,
    print_list_tasks,
)


def _callback_data_starts_with(prefix: str):
    """Фабрика func= для callback_query_handler (в telebot нет встроенного фильтра по префиксу data)."""

    def match(call):
        data = getattr(call, "data", None)
        return isinstance(data, str) and data.startswith(prefix)

    return match


def _pop_pending_or_answer_expired(bot, call, token):
    pending = pop_pending_task(token)
    if not pending:
        bot.answer_callback_query(call.id, text="Запрос устарел.")
        return None
    return pending


def _edit_callback_message(bot, call, text: str) -> None:
    msg = call.message
    bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text=text)


def register_callback_handlers(bot):
    @bot.callback_query_handler(func=_callback_data_starts_with(CB_ADD_TASK_YES_PREFIX))
    @require_allowed_user(bot)
    def add_task_confirm(call):
        token = call.data[len(CB_ADD_TASK_YES_PREFIX) :]
        pending = _pop_pending_or_answer_expired(bot, call, token)
        if not pending:
            return

        try:
            add_task(pending["description"], pending["time"] or None)
        except ValueError as exc:
            bot.answer_callback_query(call.id, text=str(exc))
            _edit_callback_message(bot, call, str(exc))
            return

        bot.answer_callback_query(call.id, text="Добавлено")
        _edit_callback_message(bot, call, f"Добавлена задача: {pending['description']}.")
        print_list_tasks(bot, call.message, list_tasks())

    @bot.callback_query_handler(func=_callback_data_starts_with(CB_ADD_TASK_NO_PREFIX))
    @require_allowed_user(bot)
    def add_task_cancel(call):
        token = call.data[len(CB_ADD_TASK_NO_PREFIX) :]
        pop_pending_task(token)
        bot.answer_callback_query(call.id, text="Отменено")
        _edit_callback_message(bot, call, "Добавление задачи отменено.")

    @bot.callback_query_handler(func=_callback_data_starts_with(CB_BULK_DELETE_YES_PREFIX))
    @require_allowed_user(bot)
    def bulk_delete_yes(call):
        token = call.data[len(CB_BULK_DELETE_YES_PREFIX) :]
        pending = _pop_pending_or_answer_expired(bot, call, token)
        if not pending:
            return
        delete_tasks(pending["task_ids"])
        bot.answer_callback_query(call.id, text="Удалено")
        _edit_callback_message(bot, call, "Задачи удалены.")
        print_list_tasks(bot, call.message, list_tasks())

    @bot.callback_query_handler(func=_callback_data_starts_with(CB_BULK_DELETE_NO_PREFIX))
    @require_allowed_user(bot)
    def bulk_delete_no(call):
        token = call.data[len(CB_BULK_DELETE_NO_PREFIX) :]
        pop_pending_task(token)
        bot.answer_callback_query(call.id, text="Отменено")
        _edit_callback_message(bot, call, "Удаление отменено.")

    @bot.callback_query_handler(func=_callback_data_starts_with(CB_BULK_COMPLETE_YES_PREFIX))
    @require_allowed_user(bot)
    def bulk_complete_yes(call):
        token = call.data[len(CB_BULK_COMPLETE_YES_PREFIX) :]
        pending = _pop_pending_or_answer_expired(bot, call, token)
        if not pending:
            return
        complete_tasks(pending["task_ids"])
        bot.answer_callback_query(call.id, text="Готово")
        _edit_callback_message(bot, call, "Задачи отмечены выполненными.")
        print_list_tasks(bot, call.message, list_tasks())

    @bot.callback_query_handler(func=_callback_data_starts_with(CB_BULK_COMPLETE_NO_PREFIX))
    @require_allowed_user(bot)
    def bulk_complete_no(call):
        token = call.data[len(CB_BULK_COMPLETE_NO_PREFIX) :]
        pop_pending_task(token)
        bot.answer_callback_query(call.id, text="Отменено")
        _edit_callback_message(bot, call, "Завершение отменено.")
