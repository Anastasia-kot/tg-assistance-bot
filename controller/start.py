from __future__ import annotations

from controller.helpers import (
    prompt_start_auth,
    reject_if_not_private,
    remind_auth,
    telegram_id_of,
)
from model.pending import clear_pending
from model.users import AUTH_NEED_PHONE, ensure_user, is_ready, reset_login
from view import (
    MSG_ASK_PHONE,
    MSG_LOGOUT,
    MSG_START_READY,
    MSG_STATUS_NEED,
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
        user = ensure_user(telegram_id)
        if is_ready(user):
            bot.send_message(
                message.chat.id,
                MSG_START_READY,
                reply_markup=remove_keyboard(),
            )
            return
        if user.get("auth_state") == AUTH_NEED_PHONE:
            prompt_start_auth(bot, message.chat.id)
            return
        remind_auth(bot, message.chat.id, user)

    @bot.message_handler(commands=["login"])
    def handle_login(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        ensure_user(telegram_id)
        clear_pending(telegram_id)
        reset_login(telegram_id, keep_phone=True)
        bot.send_message(
            message.chat.id,
            MSG_ASK_PHONE,
            reply_markup=phone_keyboard(),
        )

    @bot.message_handler(commands=["logout"])
    def handle_logout(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        ensure_user(telegram_id)
        clear_pending(telegram_id)
        reset_login(telegram_id, keep_phone=False)
        bot.send_message(
            message.chat.id,
            MSG_LOGOUT,
            reply_markup=phone_keyboard(),
        )

    @bot.message_handler(commands=["status"])
    def handle_status(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        user = ensure_user(telegram_id)
        if is_ready(user):
            bot.send_message(message.chat.id, MSG_STATUS_READY)
            return
        bot.send_message(message.chat.id, MSG_STATUS_NEED)

    @bot.message_handler(
        func=lambda m: bool(getattr(m, "text", None)) and m.text.startswith("/")
    )
    def handle_unknown_command(message):
        if reject_if_not_private(bot, message):
            return
        bot.send_message(message.chat.id, MSG_UNKNOWN_COMMAND)
