from __future__ import annotations

from controller.helpers import (
    looks_like_phone,
    normalize_phone,
    prompt_start_auth,
    reject_if_not_private,
    telegram_id_of,
    try_delete,
)
from model.stories import StoriesError, request_login_code, sign_in_code, sign_in_password, user_lock
from model.users import (
    AUTH_NEED_2FA,
    AUTH_NEED_CODE,
    AUTH_NEED_PHONE,
    AUTH_READY,
    ensure_user,
    is_ready,
    mark_ready,
    update_user,
)
from view import (
    MSG_ASK_2FA,
    MSG_ASK_CODE,
    MSG_AUTH_DONE,
    MSG_BAD_PHONE,
    MSG_CODE_SENT,
    mask_phone,
    remove_keyboard,
)


def _phone_from_message(message) -> str | None:
    contact = getattr(message, "contact", None)
    if contact is not None:
        sender_id = telegram_id_of(message)
        contact_user_id = getattr(contact, "user_id", None)
        if contact_user_id is not None and sender_id is not None:
            if int(contact_user_id) != int(sender_id):
                return None
        return normalize_phone(getattr(contact, "phone_number", "") or "")
    text = (getattr(message, "text", None) or "").strip()
    if not text:
        return None
    return normalize_phone(text)


def _send_code(bot, chat_id: int, telegram_id: int, phone: str, session_string: str | None) -> None:
    session, phone_code_hash = request_login_code(phone, session_string)
    update_user(
        telegram_id,
        phone=phone,
        session_string=session,
        phone_code_hash=phone_code_hash,
        auth_state=AUTH_NEED_CODE,
    )
    bot.send_message(
        chat_id,
        MSG_CODE_SENT.format(phone=mask_phone(phone)),
        reply_markup=remove_keyboard(),
    )


def register_login_handlers(bot):
    @bot.message_handler(content_types=["contact"])
    def handle_contact(message):
        if reject_if_not_private(bot, message):
            return
        _handle_login_message(bot, message)

    @bot.message_handler(
        func=lambda m: bool(getattr(m, "text", None)) and not m.text.startswith("/"),
        content_types=["text"],
    )
    def handle_text(message):
        if reject_if_not_private(bot, message):
            return
        _handle_login_message(bot, message)


def _handle_login_message(bot, message) -> None:
    telegram_id = telegram_id_of(message)
    if telegram_id is None:
        return
    user = ensure_user(telegram_id)
    if is_ready(user):
        bot.send_message(message.chat.id, MSG_AUTH_DONE, reply_markup=remove_keyboard())
        return

    state = user.get("auth_state") or AUTH_NEED_PHONE
    with user_lock(telegram_id):
        user = ensure_user(telegram_id)
        state = user.get("auth_state") or AUTH_NEED_PHONE
        if state == AUTH_READY:
            bot.send_message(message.chat.id, MSG_AUTH_DONE, reply_markup=remove_keyboard())
            return
        if state == AUTH_NEED_2FA:
            _handle_password(bot, message, telegram_id, user)
            return
        if state == AUTH_NEED_CODE:
            _handle_code_or_new_phone(bot, message, telegram_id, user)
            return
        _handle_phone(bot, message, telegram_id, user)


def _handle_phone(bot, message, telegram_id: int, user: dict) -> None:
    phone = _phone_from_message(message)
    try_delete(bot, message)
    if not phone:
        bot.send_message(message.chat.id, MSG_BAD_PHONE)
        return
    try:
        _send_code(bot, message.chat.id, telegram_id, phone, user.get("session_string"))
    except StoriesError as exc:
        bot.send_message(message.chat.id, exc.user_message)


def _handle_code_or_new_phone(bot, message, telegram_id: int, user: dict) -> None:
    text = (getattr(message, "text", None) or "").strip()
    contact_phone = _phone_from_message(message) if getattr(message, "contact", None) else None
    if contact_phone or (text and looks_like_phone(text) and not text.isdigit()):
        _handle_phone(bot, message, telegram_id, user)
        return

    try_delete(bot, message)
    code = "".join(ch for ch in text if ch.isdigit())
    if not code:
        bot.send_message(message.chat.id, MSG_ASK_CODE)
        return

    phone = user.get("phone")
    session_string = user.get("session_string")
    phone_code_hash = user.get("phone_code_hash")
    if not phone or not session_string or not phone_code_hash:
        prompt_start_auth(bot, message.chat.id)
        update_user(telegram_id, auth_state=AUTH_NEED_PHONE)
        return

    try:
        new_session, needs_2fa = sign_in_code(session_string, phone, code, phone_code_hash)
    except StoriesError as exc:
        saved = getattr(exc, "session_string", None)
        if saved:
            update_user(telegram_id, session_string=saved)
        bot.send_message(message.chat.id, exc.user_message)
        return

    if needs_2fa:
        update_user(
            telegram_id,
            session_string=new_session,
            auth_state=AUTH_NEED_2FA,
            clear_phone_code_hash=True,
        )
        bot.send_message(message.chat.id, MSG_ASK_2FA)
        return

    mark_ready(telegram_id, new_session)
    bot.send_message(message.chat.id, MSG_AUTH_DONE, reply_markup=remove_keyboard())


def _handle_password(bot, message, telegram_id: int, user: dict) -> None:
    password = (getattr(message, "text", None) or "").strip()
    try_delete(bot, message)
    if not password:
        bot.send_message(message.chat.id, MSG_ASK_2FA)
        return
    session_string = user.get("session_string")
    if not session_string:
        prompt_start_auth(bot, message.chat.id)
        update_user(telegram_id, auth_state=AUTH_NEED_PHONE)
        return
    try:
        new_session = sign_in_password(session_string, password)
    except StoriesError as exc:
        bot.send_message(message.chat.id, exc.user_message)
        return
    mark_ready(telegram_id, new_session)
    bot.send_message(message.chat.id, MSG_AUTH_DONE, reply_markup=remove_keyboard())
