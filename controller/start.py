from __future__ import annotations

from controller.helpers import (
    reject_if_not_private,
    telegram_id_of,
)
from model.accounts import accounts_status
from view import (
    BTN_STATUS,
    MSG_START_READY,
    MSG_UNKNOWN_COMMAND,
    main_keyboard,
)


def register_start_handlers(bot):
    @bot.message_handler(commands=["start"])
    def handle_start(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        bot.send_message(
            message.chat.id,
            MSG_START_READY,
            reply_markup=main_keyboard(),
        )

    @bot.message_handler(commands=["status"])
    def handle_status(message):
        _send_status(bot, message)

    @bot.message_handler(
        func=lambda m: (getattr(m, "text", None) or "").strip() == BTN_STATUS
    )
    def handle_status_button(message):
        _send_status(bot, message)

    @bot.message_handler(
        func=lambda m: bool(getattr(m, "text", None)) and m.text.startswith("/")
    )
    def handle_unknown_command(message):
        if reject_if_not_private(bot, message):
            return
        bot.send_message(message.chat.id, MSG_UNKNOWN_COMMAND)


def _send_status(bot, message) -> None:
    if reject_if_not_private(bot, message):
        return
    telegram_id = telegram_id_of(message)
    if telegram_id is None:
        return
    bot.send_message(
        message.chat.id,
        accounts_status(telegram_id),
        reply_markup=main_keyboard(),
    )
