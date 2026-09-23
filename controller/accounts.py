from __future__ import annotations

from controller.helpers import telegram_id_of
from model.platforms import platform_statuses
from model.vk_oauth import vk_authorize_url, vk_oauth_ready
from model.vk_retry import cancel_vk_retry
from model.vk_stories import logout_vk
from view import (
    MSG_STATUS_READY,
    MSG_TG_LOGIN_HINT,
    MSG_TG_LOGOUT_HINT,
    MSG_VK_LOGIN_HINT,
    MSG_VK_LOGOUT,
    accounts_keyboard,
    accounts_message,
    main_keyboard,
)


def account_statuses(telegram_id: int):
    login_url = vk_authorize_url(telegram_id) if vk_oauth_ready() else None
    return platform_statuses(telegram_id, vk_login_url=login_url)


def send_accounts_panel(
    bot,
    chat_id: int,
    telegram_id: int,
    *,
    intro: str,
    with_start_keyboard: bool = False,
) -> None:
    statuses = account_statuses(telegram_id)
    if with_start_keyboard:
        bot.send_message(chat_id, intro, reply_markup=main_keyboard())
        text = accounts_message("", statuses)
    else:
        text = accounts_message(intro, statuses)
    bot.send_message(
        chat_id,
        text,
        reply_markup=accounts_keyboard(statuses),
    )


def refresh_accounts_panel(bot, call, telegram_id: int, *, intro: str) -> None:
    statuses = account_statuses(telegram_id)
    try:
        bot.edit_message_text(
            accounts_message(intro, statuses),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=accounts_keyboard(statuses),
        )
    except Exception:
        send_accounts_panel(bot, call.message.chat.id, telegram_id, intro=intro)


def register_account_handlers(bot) -> None:
    @bot.callback_query_handler(func=lambda call: call.data == "acc:telegram:login")
    def handle_tg_login(call):
        bot.answer_callback_query(call.id, text=MSG_TG_LOGIN_HINT, show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "acc:telegram:logout")
    def handle_tg_logout(call):
        bot.answer_callback_query(call.id, text=MSG_TG_LOGOUT_HINT, show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "acc:vk:login")
    def handle_vk_login_missing(call):
        bot.answer_callback_query(call.id, text=MSG_VK_LOGIN_HINT, show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "acc:vk:logout")
    def handle_vk_logout_button(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        cancel_vk_retry(telegram_id)
        logout_vk(telegram_id)
        bot.answer_callback_query(call.id, text=MSG_VK_LOGOUT)
        refresh_accounts_panel(bot, call, telegram_id, intro=MSG_STATUS_READY)
