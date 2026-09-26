from __future__ import annotations

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from model.pending import PendingStory
from model.platforms import (
    PLATFORM_ORDER,
    PLATFORM_TITLES,
    PlatformStatus,
)

CB_PUBLISH_NO = "story:no"
CB_ADD_TEXT = "story:add_text"
CB_EDIT_TEXT = "story:edit_text"
CB_VK_RETRY_CANCEL = "vk:retry:cancel"
CB_VK_FLOOD_CHECK_CANCEL = "vk:flood:cancel"
CB_PUBLISH_GO = "story:publish"
CB_TOGGLE_PREFIX = "story:toggle:"
CB_LOCKED_PREFIX = "story:locked:"
CB_ACC_TG_LOGIN = "acc:telegram:login"
CB_ACC_TG_LOGOUT = "acc:telegram:logout"
CB_ACC_VK_LOGOUT = "acc:vk:logout"
CB_ACC_VK_LOGIN = "acc:vk:login"
CB_ACC_VK_METHOD_KATE = "acc:vk:method:kate"
CB_ACC_VK_METHOD_OWN = "acc:vk:method:own"
CB_ACC_VK_METHOD_CANCEL = "acc:vk:method:cancel"
CB_ACC_INFO_PREFIX = "acc:info:"

BTN_START = "Старт"

EMOJI_CHECKED = "✅"
EMOJI_UNCHECKED = "⬜"
EMOJI_LOCKED = "🔒"
EMOJI_CONNECTED = "✅"
EMOJI_DISCONNECTED = "❌"


def main_keyboard() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton(BTN_START))
    return markup


def phone_keyboard() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Отправить номер", request_contact=True))
    return markup


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def _callback_data(data) -> str | None:
    """Accept callback data string or CallbackQuery-like object."""
    if data is None:
        return None
    if isinstance(data, str):
        return data
    return getattr(data, "data", None)


def is_toggle_callback(data) -> bool:
    text = _callback_data(data)
    return bool(text and text.startswith(CB_TOGGLE_PREFIX))


def is_locked_callback(data) -> bool:
    text = _callback_data(data)
    return bool(text and text.startswith(CB_LOCKED_PREFIX))


def is_account_info_callback(data) -> bool:
    text = _callback_data(data)
    return bool(text and text.startswith(CB_ACC_INFO_PREFIX))


def account_info_key_from_callback(data: str) -> str:
    return data[len(CB_ACC_INFO_PREFIX) :]


def toggle_platform_from_callback(data: str) -> str:
    return data[len(CB_TOGGLE_PREFIX) :]


def locked_platform_from_callback(data: str) -> str:
    return data[len(CB_LOCKED_PREFIX) :]


def accounts_keyboard(statuses: list[PlatformStatus]) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    for status in statuses:
        mark = EMOJI_CONNECTED if status.connected else EMOJI_DISCONNECTED
        status_button = InlineKeyboardButton(
            f"{mark} {status.title}",
            callback_data=f"{CB_ACC_INFO_PREFIX}{status.key}",
        )
        action = (
            _logout_button(status) if status.connected else _login_button(status)
        )
        markup.row(status_button, action)
    return markup


def publish_keyboard(
    story: PendingStory | None,
    connected: frozenset[str],
    *,
    has_caption: bool = False,
) -> InlineKeyboardMarkup:
    selected = story.selected if story else frozenset()
    markup = InlineKeyboardMarkup()
    for key in PLATFORM_ORDER:
        title = PLATFORM_TITLES[key]
        if key not in connected:
            markup.row(
                InlineKeyboardButton(
                    f"{EMOJI_LOCKED} {title}",
                    callback_data=f"{CB_LOCKED_PREFIX}{key}",
                )
            )
            continue
        mark = EMOJI_CHECKED if key in selected else EMOJI_UNCHECKED
        markup.row(
            InlineKeyboardButton(
                f"{mark} {title}",
                callback_data=f"{CB_TOGGLE_PREFIX}{key}",
            )
        )
    markup.row(InlineKeyboardButton("Опубликовать", callback_data=CB_PUBLISH_GO))
    if has_caption:
        markup.row(
            InlineKeyboardButton("Изменить текст", callback_data=CB_EDIT_TEXT),
            InlineKeyboardButton("Отменить", callback_data=CB_PUBLISH_NO),
        )
        return markup
    markup.row(
        InlineKeyboardButton("Добавить текст", callback_data=CB_ADD_TEXT),
        InlineKeyboardButton("Отменить", callback_data=CB_PUBLISH_NO),
    )
    return markup


def preview_keyboard(
    story: PendingStory | None,
    connected: frozenset[str],
) -> InlineKeyboardMarkup:
    return publish_keyboard(story, connected, has_caption=True)


def vk_retry_cancel_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Отменить повтор", callback_data=CB_VK_RETRY_CANCEL),
    )
    return markup


def vk_flood_check_cancel_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            "Отменить проверку",
            callback_data=CB_VK_FLOOD_CHECK_CANCEL,
        ),
    )
    return markup


def vk_oauth_keyboard(url: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Открыть VK", url=url))
    return markup


def vk_auth_method_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Kate Mobile", callback_data=CB_ACC_VK_METHOD_KATE),
        InlineKeyboardButton("Своё приложение", callback_data=CB_ACC_VK_METHOD_OWN),
    )
    markup.row(
        InlineKeyboardButton("Отмена", callback_data=CB_ACC_VK_METHOD_CANCEL),
    )
    return markup


def _login_button(status: PlatformStatus) -> InlineKeyboardButton:
    label = f"Войти в {status.title}"
    callback = CB_ACC_VK_LOGIN if status.key == "vk" else CB_ACC_TG_LOGIN
    return InlineKeyboardButton(label, callback_data=callback)


def _logout_button(status: PlatformStatus) -> InlineKeyboardButton:
    callback = CB_ACC_VK_LOGOUT if status.key == "vk" else CB_ACC_TG_LOGOUT
    return InlineKeyboardButton(
        f"Выйти из {status.title}",
        callback_data=callback,
    )
