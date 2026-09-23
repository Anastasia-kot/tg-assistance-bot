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
CB_PUBLISH_GO = "story:publish"
CB_TOGGLE_PREFIX = "story:toggle:"
CB_LOCKED_PREFIX = "story:locked:"
CB_ACC_TG_LOGIN = "acc:telegram:login"
CB_ACC_TG_LOGOUT = "acc:telegram:logout"
CB_ACC_VK_LOGOUT = "acc:vk:logout"
CB_ACC_VK_LOGIN = "acc:vk:login"

BTN_START = "Старт"

EMOJI_CHECKED = "✅"
EMOJI_UNCHECKED = "⬜"
EMOJI_LOCKED = "🔒"


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


def is_toggle_callback(data: str | None) -> bool:
    return bool(data and data.startswith(CB_TOGGLE_PREFIX))


def is_locked_callback(data: str | None) -> bool:
    return bool(data and data.startswith(CB_LOCKED_PREFIX))


def toggle_platform_from_callback(data: str) -> str:
    return data[len(CB_TOGGLE_PREFIX) :]


def locked_platform_from_callback(data: str) -> str:
    return data[len(CB_LOCKED_PREFIX) :]


def accounts_keyboard(statuses: list[PlatformStatus]) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    for status in statuses:
        login = _login_button(status)
        logout = InlineKeyboardButton(
            f"Выйти из {status.title}",
            callback_data=(
                CB_ACC_VK_LOGOUT if status.key == "vk" else CB_ACC_TG_LOGOUT
            ),
        )
        markup.row(login, logout)
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


def vk_oauth_keyboard(url: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Открыть VK", url=url))
    return markup


def _login_button(status: PlatformStatus) -> InlineKeyboardButton:
    label = f"Войти в {status.title}"
    if status.key == "vk" and status.login_url:
        return InlineKeyboardButton(label, url=status.login_url)
    callback = CB_ACC_VK_LOGIN if status.key == "vk" else CB_ACC_TG_LOGIN
    return InlineKeyboardButton(label, callback_data=callback)
