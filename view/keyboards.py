from __future__ import annotations

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

CB_PUBLISH_YES = "story:yes"
CB_PUBLISH_TELEGRAM = "story:publish:telegram"
CB_PUBLISH_VK = "story:publish:vk"
CB_PUBLISH_BOTH = "story:publish:both"
CB_PUBLISH_NO = "story:no"
CB_ADD_TEXT = "story:add_text"
CB_EDIT_TEXT = "story:edit_text"
CB_VK_RETRY_CANCEL = "vk:retry:cancel"


def phone_keyboard() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Отправить номер", request_contact=True))
    return markup


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def _publish_target_rows(markup: InlineKeyboardMarkup) -> None:
    markup.row(
        InlineKeyboardButton("Telegram", callback_data=CB_PUBLISH_TELEGRAM),
        InlineKeyboardButton("VK", callback_data=CB_PUBLISH_VK),
    )
    markup.row(
        InlineKeyboardButton("Оба", callback_data=CB_PUBLISH_BOTH),
    )


def publish_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    _publish_target_rows(markup)
    markup.row(
        InlineKeyboardButton("Добавить текст", callback_data=CB_ADD_TEXT),
        InlineKeyboardButton("Отменить", callback_data=CB_PUBLISH_NO),
    )
    return markup


def preview_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    _publish_target_rows(markup)
    markup.row(
        InlineKeyboardButton("Изменить текст", callback_data=CB_EDIT_TEXT),
        InlineKeyboardButton("Отменить", callback_data=CB_PUBLISH_NO),
    )
    return markup


def vk_retry_cancel_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Отменить повтор", callback_data=CB_VK_RETRY_CANCEL),
    )
    return markup
