from __future__ import annotations

from controller.helpers import telegram_id_of
from controller.vk_login import (
    send_vk_method_picker,
    start_kate_login,
    start_own_app_login,
)
from model.platforms import platform_statuses
from model.vk_retry import cancel_vk_retry
from model.vk_stories import logout_vk
from view import (
    CB_ACC_VK_METHOD_CANCEL,
    CB_ACC_VK_METHOD_KATE,
    CB_ACC_VK_METHOD_OWN,
    MSG_STATUS_READY,
    MSG_TG_LOGIN_HINT,
    MSG_TG_LOGOUT_HINT,
    MSG_VK_LOGOUT,
    MSG_VK_METHOD_CANCELLED,
    accounts_keyboard,
    accounts_message,
    account_info_key_from_callback,
    is_account_info_callback,
    main_keyboard,
)


def account_statuses(telegram_id: int):
    return platform_statuses(telegram_id)


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
    @bot.callback_query_handler(func=lambda call: is_account_info_callback(call.data))
    def handle_account_info(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        key = account_info_key_from_callback(call.data or "")
        detail = next(
            (item.detail for item in account_statuses(telegram_id) if item.key == key),
            None,
        )
        bot.answer_callback_query(call.id, text=detail or "Нет данных", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "acc:telegram:login")
    def handle_tg_login(call):
        bot.answer_callback_query(call.id, text=MSG_TG_LOGIN_HINT, show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "acc:telegram:logout")
    def handle_tg_logout(call):
        bot.answer_callback_query(call.id, text=MSG_TG_LOGOUT_HINT, show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "acc:vk:login")
    def handle_vk_login_button(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        bot.answer_callback_query(call.id)
        send_vk_method_picker(bot, call.message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == CB_ACC_VK_METHOD_KATE)
    def handle_vk_method_kate(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        bot.answer_callback_query(call.id)
        start_kate_login(bot, call.message.chat.id, telegram_id)

    @bot.callback_query_handler(func=lambda call: call.data == CB_ACC_VK_METHOD_OWN)
    def handle_vk_method_own(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        bot.answer_callback_query(call.id)
        start_own_app_login(bot, call.message.chat.id, telegram_id)

    @bot.callback_query_handler(func=lambda call: call.data == CB_ACC_VK_METHOD_CANCEL)
    def handle_vk_method_cancel(call):
        bot.answer_callback_query(call.id, text=MSG_VK_METHOD_CANCELLED)
        try:
            bot.edit_message_text(
                MSG_VK_METHOD_CANCELLED,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
            )
        except Exception:
            bot.send_message(call.message.chat.id, MSG_VK_METHOD_CANCELLED)

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
