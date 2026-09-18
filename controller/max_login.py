from __future__ import annotations

import io

import qrcode

from controller.helpers import (
    normalize_phone,
    reject_if_not_private,
    telegram_id_of,
    try_delete,
)
from model.locks import user_lock
from model.max_auth import (
    MAX_AUTH_CODE,
    MAX_AUTH_PASSWORD,
    MAX_AUTH_PHONE,
    accept_max_auth_risk,
    begin_max_auth,
    clear_max_auth,
    get_max_auth,
    select_max_qr_auth,
    select_max_sms_auth,
    set_max_code_requested,
    set_max_password_requested,
)
from model.max_stories import (
    MaxPasswordRequired,
    MaxStoriesError,
    confirm_max_login_code,
    confirm_max_password,
    login_max_by_qr,
    logout_max,
    request_max_login_code,
    validate_max_session,
    is_web_qr_session,
)
from view import (
    CB_MAX_AUTH_ACCEPT,
    CB_MAX_AUTH_CANCEL,
    CB_MAX_AUTH_QR,
    CB_MAX_AUTH_SMS,
    MSG_BAD_PHONE,
    MSG_MAX_ASK_2FA,
    MSG_MAX_ASK_CODE,
    MSG_MAX_ASK_PHONE,
    MSG_MAX_AUTH_CANCELLED,
    MSG_MAX_CHOOSE_AUTH,
    MSG_MAX_AUTH_DONE,
    MSG_MAX_AUTH_WARNING,
    MSG_MAX_CODE_SENT,
    MSG_MAX_LOGOUT,
    MSG_MAX_SCAN_QR,
    MSG_MAX_STATUS_NEED,
    MSG_MAX_STATUS_READY,
    MSG_MAX_STATUS_WEB,
    main_keyboard,
    max_auth_method_keyboard,
    max_auth_warning_keyboard,
    phone_keyboard,
)

def _phone_from_message(message) -> str | None:
    contact = getattr(message, "contact", None)
    if contact is not None:
        sender_id = telegram_id_of(message)
        contact_user_id = getattr(contact, "user_id", None)
        is_another_contact = (
            contact_user_id is not None
            and sender_id is not None
            and int(contact_user_id) != int(sender_id)
        )
        if is_another_contact:
            return None
        return normalize_phone(getattr(contact, "phone_number", "") or "")
    return normalize_phone((getattr(message, "text", None) or "").strip())


def _is_max_auth_text(message) -> bool:
    telegram_id = telegram_id_of(message)
    state = get_max_auth(telegram_id) if telegram_id is not None else None
    return bool(
        state
        and state.step in {MAX_AUTH_PHONE, MAX_AUTH_CODE, MAX_AUTH_PASSWORD}
        and getattr(message, "text", None)
    )


def _is_max_auth_phone_contact(message) -> bool:
    telegram_id = telegram_id_of(message)
    if telegram_id is None:
        return False
    state = get_max_auth(telegram_id)
    return bool(state and state.step == MAX_AUTH_PHONE)


def _send_auth_error(bot, chat_id: int, error: MaxStoriesError) -> None:
    bot.send_message(chat_id, error.user_message)


def register_max_login_handlers(bot) -> None:
    @bot.message_handler(commands=["max_login"])
    def handle_max_login(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        begin_max_auth(telegram_id)
        bot.send_message(
            message.chat.id,
            MSG_MAX_AUTH_WARNING,
            reply_markup=max_auth_warning_keyboard(),
        )

    @bot.message_handler(commands=["max_status"])
    def handle_max_status(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        with user_lock(telegram_id):
            if is_web_qr_session(telegram_id):
                bot.send_message(message.chat.id, MSG_MAX_STATUS_WEB)
                return
            is_ready = validate_max_session(telegram_id)
        bot.send_message(
            message.chat.id,
            MSG_MAX_STATUS_READY if is_ready else MSG_MAX_STATUS_NEED,
        )

    @bot.message_handler(commands=["max_logout"])
    def handle_max_logout(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        clear_max_auth(telegram_id)
        with user_lock(telegram_id):
            logout_max(telegram_id)
        bot.send_message(
            message.chat.id,
            MSG_MAX_LOGOUT,
            reply_markup=main_keyboard(),
        )

    @bot.callback_query_handler(
        func=lambda call: call.data == CB_MAX_AUTH_ACCEPT
    )
    def handle_max_auth_accept(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        state = accept_max_auth_risk(telegram_id)
        if state is None:
            bot.answer_callback_query(call.id, text="Запустите /max_login")
            return
        bot.answer_callback_query(call.id)
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
        bot.send_message(
            call.message.chat.id,
            MSG_MAX_CHOOSE_AUTH,
            reply_markup=max_auth_method_keyboard(),
        )

    @bot.callback_query_handler(func=lambda call: call.data == CB_MAX_AUTH_QR)
    def handle_max_auth_qr(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        state = select_max_qr_auth(telegram_id)
        if state is None:
            bot.answer_callback_query(call.id, text="Запустите /max_login")
            return
        bot.answer_callback_query(call.id)
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )

        def show_qr(qr_url: str) -> None:
            image = qrcode.make(qr_url)
            buffer = io.BytesIO()
            buffer.name = "max-login.png"
            image.save(buffer, format="PNG")
            buffer.seek(0)
            bot.send_photo(
                call.message.chat.id,
                buffer,
                caption=MSG_MAX_SCAN_QR,
            )

        try:
            with user_lock(telegram_id):
                name = login_max_by_qr(telegram_id, show_qr)
        except MaxStoriesError as error:
            clear_max_auth(telegram_id)
            _send_auth_error(bot, call.message.chat.id, error)
            return
        clear_max_auth(telegram_id)
        bot.send_message(
            call.message.chat.id,
            MSG_MAX_AUTH_DONE.format(name=name),
            reply_markup=main_keyboard(),
        )

    @bot.callback_query_handler(func=lambda call: call.data == CB_MAX_AUTH_SMS)
    def handle_max_auth_sms(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        state = select_max_sms_auth(telegram_id)
        if state is None:
            bot.answer_callback_query(call.id, text="Запустите /max_login")
            return
        bot.answer_callback_query(call.id)
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
        bot.send_message(
            call.message.chat.id,
            MSG_MAX_ASK_PHONE,
            reply_markup=phone_keyboard(),
        )

    @bot.callback_query_handler(
        func=lambda call: call.data == CB_MAX_AUTH_CANCEL
    )
    def handle_max_auth_cancel(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        clear_max_auth(telegram_id)
        bot.answer_callback_query(call.id, text="Отменено")
        bot.edit_message_text(
            MSG_MAX_AUTH_CANCELLED,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )

    @bot.message_handler(
        func=_is_max_auth_phone_contact,
        content_types=["contact"],
    )
    def handle_max_contact(message):
        if reject_if_not_private(bot, message):
            return
        _handle_max_auth_message(bot, message)

    @bot.message_handler(func=_is_max_auth_text, content_types=["text"])
    def handle_max_auth_text(message):
        if reject_if_not_private(bot, message):
            return
        _handle_max_auth_message(bot, message)


def _handle_max_auth_message(bot, message) -> None:
    telegram_id = telegram_id_of(message)
    if telegram_id is None:
        return
    state = get_max_auth(telegram_id)
    if state is None:
        return
    if state.step == MAX_AUTH_PHONE:
        _handle_max_phone(bot, message, telegram_id)
        return
    if state.step == MAX_AUTH_CODE:
        _handle_max_code(bot, message, telegram_id, state.auth_token)
        return
    if state.step == MAX_AUTH_PASSWORD:
        _handle_max_password(bot, message, telegram_id, state.track_id)


def _handle_max_phone(bot, message, telegram_id: int) -> None:
    phone = _phone_from_message(message)
    try_delete(bot, message)
    if phone is None:
        bot.send_message(message.chat.id, MSG_BAD_PHONE)
        return
    try:
        with user_lock(telegram_id):
            auth_token = request_max_login_code(telegram_id, phone)
    except MaxStoriesError as error:
        _send_auth_error(bot, message.chat.id, error)
        return
    set_max_code_requested(telegram_id, phone, auth_token)
    bot.send_message(
        message.chat.id,
        MSG_MAX_CODE_SENT,
        reply_markup=main_keyboard(),
    )


def _handle_max_code(
    bot,
    message,
    telegram_id: int,
    auth_token: str | None,
) -> None:
    code = "".join(
        character
        for character in (getattr(message, "text", None) or "")
        if character.isdigit()
    )
    try_delete(bot, message)
    if not code:
        bot.send_message(message.chat.id, MSG_MAX_ASK_CODE)
        return
    if not auth_token:
        clear_max_auth(telegram_id)
        bot.send_message(message.chat.id, "Сессия входа устарела. Начните /max_login заново.")
        return
    try:
        with user_lock(telegram_id):
            name = confirm_max_login_code(telegram_id, code, auth_token)
    except MaxPasswordRequired as error:
        set_max_password_requested(telegram_id, error.track_id)
        bot.send_message(message.chat.id, MSG_MAX_ASK_2FA)
        return
    except MaxStoriesError as error:
        _send_auth_error(bot, message.chat.id, error)
        return
    clear_max_auth(telegram_id)
    bot.send_message(
        message.chat.id,
        MSG_MAX_AUTH_DONE.format(name=name),
        reply_markup=main_keyboard(),
    )


def _handle_max_password(
    bot,
    message,
    telegram_id: int,
    track_id: str | None,
) -> None:
    password = (getattr(message, "text", None) or "").strip()
    try_delete(bot, message)
    if not password:
        bot.send_message(message.chat.id, MSG_MAX_ASK_2FA)
        return
    if not track_id:
        clear_max_auth(telegram_id)
        bot.send_message(message.chat.id, "Сессия входа устарела. Начните /max_login заново.")
        return
    try:
        with user_lock(telegram_id):
            name = confirm_max_password(telegram_id, password, track_id)
    except MaxStoriesError as error:
        _send_auth_error(bot, message.chat.id, error)
        return
    clear_max_auth(telegram_id)
    bot.send_message(
        message.chat.id,
        MSG_MAX_AUTH_DONE.format(name=name),
        reply_markup=main_keyboard(),
    )
