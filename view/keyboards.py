from __future__ import annotations

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

CB_PUBLISH_YES = "story:yes"
CB_PUBLISH_NO = "story:no"
CB_ADD_TEXT = "story:add_text"
CB_EDIT_TEXT = "story:edit_text"


def phone_keyboard() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Отправить номер", request_contact=True))
    return markup


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def publish_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Опубликовать без текста", callback_data=CB_PUBLISH_YES),
    )
    markup.row(
        InlineKeyboardButton("Добавить текст", callback_data=CB_ADD_TEXT),
        InlineKeyboardButton("Отменить", callback_data=CB_PUBLISH_NO),
    )
    return markup


def preview_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Опубликовать", callback_data=CB_PUBLISH_YES),
    )
    markup.row(
        InlineKeyboardButton("Изменить текст", callback_data=CB_EDIT_TEXT),
        InlineKeyboardButton("Отменить", callback_data=CB_PUBLISH_NO),
    )
    return markup
