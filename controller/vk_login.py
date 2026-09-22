from __future__ import annotations

from controller.helpers import reject_if_not_private, telegram_id_of
from model.stories import user_lock
from model.vk_oauth import vk_authorize_url, vk_oauth_ready
from model.vk_retry import cancel_vk_retry
from model.vk_stories import (
    check_vk_token,
    has_vk_session,
    logout_vk,
    vk_account_label,
)
from view import (
    MSG_VK_ASK_OAUTH,
    MSG_VK_LOGOUT,
    MSG_VK_OAUTH_NOT_CONFIGURED,
    MSG_VK_STATUS_NEED,
    MSG_VK_STATUS_READY,
    MSG_VK_TOKEN_OK,
    remove_keyboard,
    vk_oauth_keyboard,
)


def register_vk_login_handlers(bot) -> None:
    @bot.message_handler(commands=["vk_login"])
    def handle_vk_login(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        if not vk_oauth_ready():
            bot.send_message(message.chat.id, MSG_VK_OAUTH_NOT_CONFIGURED)
            return
        bot.send_message(
            message.chat.id,
            MSG_VK_ASK_OAUTH,
            reply_markup=vk_oauth_keyboard(vk_authorize_url(telegram_id)),
        )

    @bot.message_handler(commands=["vk_status"])
    def handle_vk_status(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        if not has_vk_session(telegram_id):
            bot.send_message(message.chat.id, MSG_VK_STATUS_NEED)
            return
        with user_lock(telegram_id):
            status = check_vk_token(telegram_id)
        if not status["ok"]:
            bot.send_message(
                message.chat.id,
                status["error"] or MSG_VK_STATUS_NEED,
            )
            return
        name = vk_account_label(telegram_id) or "VK"
        bot.send_message(
            message.chat.id,
            f"{MSG_VK_STATUS_READY.format(name=name)}\n{MSG_VK_TOKEN_OK}",
        )

    @bot.message_handler(commands=["vk_logout"])
    def handle_vk_logout(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        cancel_vk_retry(telegram_id)
        with user_lock(telegram_id):
            logout_vk(telegram_id)
        bot.send_message(
            message.chat.id,
            MSG_VK_LOGOUT,
            reply_markup=remove_keyboard(),
        )
