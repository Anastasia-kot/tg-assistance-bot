from __future__ import annotations

from controller.helpers import (
    reject_if_not_private,
    telegram_id_of,
    try_delete,
)
from model.stories import user_lock
from model.vk_auth import begin_vk_login, clear_vk_login, is_waiting_vk_token
from model.vk_retry import cancel_vk_retry
from model.vk_stories import (
    VkFloodError,
    VkStoriesError,
    check_vk_token,
    has_vk_session,
    logout_vk,
    parse_vk_token,
    save_vk_token,
    vk_account_label,
    vk_oauth_url,
)
from view import (
    MSG_VK_ASK_TOKEN,
    MSG_VK_AUTH_DONE,
    MSG_VK_LOGOUT,
    MSG_VK_STATUS_NEED,
    MSG_VK_STATUS_READY,
    MSG_VK_TOKEN_OK,
    remove_keyboard,
)


def _is_vk_token_message(message) -> bool:
    telegram_id = telegram_id_of(message)
    if telegram_id is None or not getattr(message, "text", None):
        return False
    if message.text.startswith("/"):
        return False
    return is_waiting_vk_token(telegram_id)


def register_vk_login_handlers(bot) -> None:
    @bot.message_handler(commands=["vk_login"])
    def handle_vk_login(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        begin_vk_login(telegram_id)
        bot.send_message(
            message.chat.id,
            MSG_VK_ASK_TOKEN.format(url=vk_oauth_url()),
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
        clear_vk_login(telegram_id)
        cancel_vk_retry(telegram_id)
        with user_lock(telegram_id):
            logout_vk(telegram_id)
        bot.send_message(
            message.chat.id,
            MSG_VK_LOGOUT,
            reply_markup=remove_keyboard(),
        )

    @bot.message_handler(func=_is_vk_token_message, content_types=["text"])
    def handle_vk_token(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        token = parse_vk_token(message.text or "")
        try_delete(bot, message)
        if not token or len(token) < 20:
            bot.send_message(
                message.chat.id,
                MSG_VK_ASK_TOKEN.format(url=vk_oauth_url()),
            )
            return
        try:
            with user_lock(telegram_id):
                profile = save_vk_token(telegram_id, token)
        except VkFloodError as error:
            clear_vk_login(telegram_id)
            bot.send_message(message.chat.id, error.user_message)
            return
        except VkStoriesError as error:
            bot.send_message(message.chat.id, error.user_message)
            return
        clear_vk_login(telegram_id)
        name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or "VK"
        bot.send_message(
            message.chat.id,
            MSG_VK_AUTH_DONE.format(name=name),
            reply_markup=remove_keyboard(),
        )
