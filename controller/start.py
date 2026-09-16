from __future__ import annotations

from config import business_connection_id
from controller.helpers import (
    reject_if_not_private,
    telegram_id_of,
)
from model.pending import clear_pending
from model.users import ensure_user, has_app_keys, reset_login
from view import (
    MSG_ASK_KEYS,
    MSG_ASK_PHONE,
    MSG_BUSINESS_CONNECTION_MISSING,
    MSG_LOGOUT,
    MSG_START_READY,
    MSG_STATUS_READY,
    MSG_UNKNOWN_COMMAND,
    phone_keyboard,
    remove_keyboard,
)


def register_start_handlers(bot):
    @bot.message_handler(commands=["start"])
    def handle_start(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        if business_connection_id() is None:
            bot.send_message(message.chat.id, MSG_BUSINESS_CONNECTION_MISSING)
            return
        bot.send_message(
            message.chat.id,
            MSG_START_READY,
            reply_markup=remove_keyboard(),
        )

    @bot.message_handler(commands=["login"])
    def handle_login(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        ensure_user(telegram_id)
        clear_pending(telegram_id)
        user = reset_login(telegram_id, keep_phone=True, keep_keys=True)
        if has_app_keys(user):
            bot.send_message(
                message.chat.id,
                MSG_ASK_PHONE,
                reply_markup=phone_keyboard(),
            )
            return
        bot.send_message(message.chat.id, MSG_ASK_KEYS)

    @bot.message_handler(commands=["logout"])
    def handle_logout(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        ensure_user(telegram_id)
        clear_pending(telegram_id)
        reset_login(telegram_id, keep_phone=False, keep_keys=False)
        bot.send_message(message.chat.id, MSG_LOGOUT)

    @bot.message_handler(commands=["status"])
    def handle_status(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        if business_connection_id() is None:
            bot.send_message(message.chat.id, MSG_BUSINESS_CONNECTION_MISSING)
            return
        bot.send_message(message.chat.id, MSG_STATUS_READY)

    @bot.message_handler(
        func=lambda m: bool(getattr(m, "text", None)) and m.text.startswith("/")
    )
    def handle_unknown_command(message):
        if reject_if_not_private(bot, message):
            return
        bot.send_message(message.chat.id, MSG_UNKNOWN_COMMAND)
