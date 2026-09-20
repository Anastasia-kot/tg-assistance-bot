from __future__ import annotations

from controller.helpers import (
    reject_if_not_private,
    telegram_id_of,
    try_delete,
)
from model.ig_stories import (
    IgStoriesError,
    IgTwoFactorRequired,
    login_instagram,
    logout_ig,
)
from model.locks import user_lock
from model.max_auth import clear_max_auth
from model.social_auth import (
    IG_2FA,
    IG_PASSWORD,
    IG_USERNAME,
    VK_TOKEN,
    WA_INSTANCE,
    WA_TOKEN,
    begin_social_auth,
    clear_social_auth,
    get_social_auth,
    set_social_auth,
)
from model.vk_stories import (
    VkStoriesError,
    logout_vk,
    save_vk_token,
    validate_vk_session,
    vk_account_label,
    vk_oauth_url,
)
from model.wa_stories import WaStoriesError, logout_wa, save_wa_credentials
from view import (
    BTN_STATUS,
    MSG_IG_ASK_2FA,
    MSG_IG_ASK_PASSWORD,
    MSG_IG_ASK_USERNAME,
    MSG_IG_AUTH_DONE,
    MSG_IG_AUTH_WARNING,
    MSG_IG_LOGOUT,
    MSG_VK_ASK_TOKEN,
    MSG_VK_AUTH_DONE,
    MSG_VK_LOGOUT,
    MSG_VK_STATUS_NEED,
    MSG_VK_STATUS_READY,
    MSG_WA_ASK_INSTANCE,
    MSG_WA_ASK_TOKEN,
    MSG_WA_AUTH_DONE,
    MSG_WA_AUTH_WARNING,
    MSG_WA_LOGOUT,
    main_keyboard,
)


def _is_social_auth_text(message) -> bool:
    telegram_id = telegram_id_of(message)
    if telegram_id is None or not getattr(message, "text", None):
        return False
    return bool(
        get_social_auth(telegram_id) is not None
        and getattr(message, "text", None)
        and message.text.strip() != BTN_STATUS
    )


def register_social_login_handlers(bot) -> None:
    @bot.message_handler(commands=["wa_login"])
    def handle_wa_login(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        clear_max_auth(telegram_id)
        begin_social_auth(telegram_id, "whatsapp", WA_INSTANCE)
        bot.send_message(message.chat.id, MSG_WA_AUTH_WARNING)
        bot.send_message(message.chat.id, MSG_WA_ASK_INSTANCE)

    @bot.message_handler(commands=["vk_login"])
    def handle_vk_login(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        clear_max_auth(telegram_id)
        begin_social_auth(telegram_id, "vk", VK_TOKEN)
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
        with user_lock(telegram_id):
            is_ready = validate_vk_session(telegram_id)
        if not is_ready:
            bot.send_message(message.chat.id, MSG_VK_STATUS_NEED)
            return
        name = vk_account_label(telegram_id) or "VK"
        bot.send_message(
            message.chat.id,
            MSG_VK_STATUS_READY.format(name=name),
        )

    @bot.message_handler(commands=["ig_login"])
    def handle_ig_login(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        clear_max_auth(telegram_id)
        begin_social_auth(telegram_id, "instagram", IG_USERNAME)
        bot.send_message(message.chat.id, MSG_IG_AUTH_WARNING)
        bot.send_message(message.chat.id, MSG_IG_ASK_USERNAME)

    @bot.message_handler(commands=["wa_logout"])
    def handle_wa_logout(message):
        _logout(bot, message, logout_wa, MSG_WA_LOGOUT)

    @bot.message_handler(commands=["vk_logout"])
    def handle_vk_logout(message):
        _logout(bot, message, logout_vk, MSG_VK_LOGOUT)

    @bot.message_handler(commands=["ig_logout"])
    def handle_ig_logout(message):
        _logout(bot, message, logout_ig, MSG_IG_LOGOUT)

    @bot.message_handler(func=_is_social_auth_text, content_types=["text"])
    def handle_social_auth_text(message):
        if reject_if_not_private(bot, message):
            return
        _handle_social_auth_message(bot, message)


def _logout(bot, message, logout_fn, done_text: str) -> None:
    if reject_if_not_private(bot, message):
        return
    telegram_id = telegram_id_of(message)
    if telegram_id is None:
        return
    clear_social_auth(telegram_id)
    with user_lock(telegram_id):
        logout_fn(telegram_id)
    bot.send_message(message.chat.id, done_text, reply_markup=main_keyboard())


def _handle_social_auth_message(bot, message) -> None:
    telegram_id = telegram_id_of(message)
    if telegram_id is None:
        return
    state = get_social_auth(telegram_id)
    if state is None:
        return
    text = (message.text or "").strip()
    if state.step in {WA_TOKEN, VK_TOKEN, IG_PASSWORD, IG_2FA}:
        try_delete(bot, message)
    if not text or text.startswith("/"):
        return
    if state.step == WA_INSTANCE:
        _save_instance(bot, message, telegram_id, text)
        return
    if state.step == WA_TOKEN:
        _finish_wa(bot, message, telegram_id, state.instance_id, text)
        return
    if state.step == VK_TOKEN:
        _finish_vk(bot, message, telegram_id, text)
        return
    if state.step == IG_USERNAME:
        set_social_auth(telegram_id, username=text, step=IG_PASSWORD)
        bot.send_message(message.chat.id, MSG_IG_ASK_PASSWORD)
        return
    if state.step == IG_PASSWORD:
        _finish_ig(bot, message, telegram_id, state.username or "", text)
        return
    if state.step == IG_2FA:
        _finish_ig(
            bot,
            message,
            telegram_id,
            state.username or "",
            state.password or "",
            text,
        )


def _save_instance(bot, message, telegram_id: int, instance_id: str) -> None:
    digits = "".join(character for character in instance_id if character.isdigit())
    if len(digits) < 4:
        bot.send_message(message.chat.id, MSG_WA_ASK_INSTANCE)
        return
    set_social_auth(telegram_id, instance_id=digits, step=WA_TOKEN)
    bot.send_message(message.chat.id, MSG_WA_ASK_TOKEN)


def _finish_wa(bot, message, telegram_id: int, instance_id: str | None, token: str) -> None:
    if not instance_id:
        clear_social_auth(telegram_id)
        bot.send_message(message.chat.id, "Сессия входа устарела. Начните /wa_login заново.")
        return
    try:
        with user_lock(telegram_id):
            state = save_wa_credentials(telegram_id, instance_id, token)
    except WaStoriesError as error:
        bot.send_message(message.chat.id, error.user_message)
        return
    clear_social_auth(telegram_id)
    bot.send_message(
        message.chat.id,
        MSG_WA_AUTH_DONE.format(state=state),
        reply_markup=main_keyboard(),
    )


def _extract_vk_token(raw: str) -> str:
    text = raw.strip()
    if "error=" in text and "access_token=" not in text:
        return ""
    if "access_token=" in text:
        after = text.split("access_token=", 1)[1]
        token = after.split("&", 1)[0].strip()
        return token
    return text


def _finish_vk(bot, message, telegram_id: int, token_raw: str) -> None:
    token = _extract_vk_token(token_raw)
    if not token or len(token) < 20:
        bot.send_message(
            message.chat.id,
            MSG_VK_ASK_TOKEN.format(url=vk_oauth_url()),
        )
        return
    try:
        with user_lock(telegram_id):
            profile = save_vk_token(telegram_id, token)
    except VkStoriesError as error:
        bot.send_message(message.chat.id, error.user_message)
        return
    clear_social_auth(telegram_id)
    name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or "VK"
    bot.send_message(
        message.chat.id,
        MSG_VK_AUTH_DONE.format(name=name),
        reply_markup=main_keyboard(),
    )


def _finish_ig(
    bot,
    message,
    telegram_id: int,
    username: str,
    password: str,
    code: str | None = None,
) -> None:
    if not username or not password:
        clear_social_auth(telegram_id)
        bot.send_message(message.chat.id, "Сессия входа устарела. Начните /ig_login заново.")
        return
    try:
        with user_lock(telegram_id):
            name = login_instagram(telegram_id, username, password, code)
    except IgTwoFactorRequired:
        set_social_auth(
            telegram_id,
            username=username,
            password=password,
            step=IG_2FA,
        )
        bot.send_message(message.chat.id, MSG_IG_ASK_2FA)
        return
    except IgStoriesError as error:
        bot.send_message(message.chat.id, error.user_message)
        return
    clear_social_auth(telegram_id)
    bot.send_message(
        message.chat.id,
        MSG_IG_AUTH_DONE.format(name=name),
        reply_markup=main_keyboard(),
    )
