from __future__ import annotations

from controller.helpers import reject_if_not_private, telegram_id_of, try_delete
from model.stories import user_lock
from model.vk_auth import (
    begin_vk_token_wait,
    clear_vk_token_wait,
    is_waiting_vk_token,
)
from model.vk_oauth import (
    AUTH_METHOD_KATE,
    AUTH_METHOD_OWN,
    kate_authorize_url,
    own_app_auth_ready,
    vk_authorize_url,
    vk_callback_reachable,
    vk_oauth_ready,
)
from model.vk_flood_check import (
    MAX_FLOOD_CHECKS,
    cancel_vk_flood_check,
    schedule_vk_flood_check,
)
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
)
from view import (
    MSG_STATUS_READY,
    MSG_VK_ASK_KATE,
    MSG_VK_ASK_METHOD,
    MSG_VK_ASK_OAUTH,
    MSG_VK_ASK_TOKEN_AGAIN,
    MSG_VK_AUTH_DONE,
    MSG_VK_CALLBACK_UNREACHABLE,
    MSG_VK_FLOOD_CHECK_SCHEDULED,
    MSG_VK_LOGOUT,
    MSG_VK_OAUTH_NOT_CONFIGURED,
    MSG_VK_STATUS_NEED,
    MSG_VK_STATUS_READY,
    MSG_VK_TOKEN_OK,
    main_keyboard,
    vk_auth_method_keyboard,
    vk_flood_check_cancel_keyboard,
    vk_oauth_keyboard,
)


def _is_vk_token_message(message) -> bool:
    telegram_id = telegram_id_of(message)
    if telegram_id is None or not getattr(message, "text", None):
        return False
    if message.text.startswith("/"):
        return False
    return is_waiting_vk_token(telegram_id)


def send_vk_method_picker(bot, chat_id: int) -> None:
    bot.send_message(
        chat_id,
        MSG_VK_ASK_METHOD,
        reply_markup=vk_auth_method_keyboard(),
    )


def start_kate_login(bot, chat_id: int, telegram_id: int) -> None:
    begin_vk_token_wait(telegram_id)
    bot.send_message(
        chat_id,
        MSG_VK_ASK_KATE,
        reply_markup=vk_oauth_keyboard(kate_authorize_url()),
    )


def start_own_app_login(bot, chat_id: int, telegram_id: int) -> None:
    clear_vk_token_wait(telegram_id)
    if not own_app_auth_ready():
        bot.send_message(chat_id, MSG_VK_OAUTH_NOT_CONFIGURED)
        return
    if not vk_callback_reachable():
        bot.send_message(chat_id, MSG_VK_CALLBACK_UNREACHABLE)
        return
    bot.send_message(
        chat_id,
        MSG_VK_ASK_OAUTH,
        reply_markup=vk_oauth_keyboard(vk_authorize_url(telegram_id)),
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
        send_vk_method_picker(bot, message.chat.id)

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
        clear_vk_token_wait(telegram_id)
        cancel_vk_retry(telegram_id)
        cancel_vk_flood_check(telegram_id)
        with user_lock(telegram_id):
            logout_vk(telegram_id)
        bot.send_message(
            message.chat.id,
            MSG_VK_LOGOUT,
            reply_markup=main_keyboard(),
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
            bot.send_message(message.chat.id, MSG_VK_ASK_TOKEN_AGAIN)
            return
        try:
            with user_lock(telegram_id):
                profile = save_vk_token(
                    telegram_id,
                    token,
                    auth_method=AUTH_METHOD_KATE,
                )
        except VkFloodError as error:
            clear_vk_token_wait(telegram_id)
            bot.send_message(message.chat.id, error.user_message)
            delay = schedule_vk_flood_check(
                bot,
                telegram_id,
                message.chat.id,
                attempt=1,
            )
            if delay is not None:
                bot.send_message(
                    message.chat.id,
                    MSG_VK_FLOOD_CHECK_SCHEDULED.format(
                        minutes=delay,
                        attempt=1,
                        max_attempts=MAX_FLOOD_CHECKS,
                        error=error.user_message,
                    ),
                    reply_markup=vk_flood_check_cancel_keyboard(),
                )
            return
        except VkStoriesError as error:
            bot.send_message(message.chat.id, error.user_message)
            return
        clear_vk_token_wait(telegram_id)
        name = (
            f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
            or "VK"
        )
        bot.send_message(
            message.chat.id,
            MSG_VK_AUTH_DONE.format(name=name),
            reply_markup=main_keyboard(),
        )
        from controller.accounts import send_accounts_panel

        send_accounts_panel(
            bot,
            message.chat.id,
            telegram_id,
            intro=MSG_STATUS_READY,
        )
