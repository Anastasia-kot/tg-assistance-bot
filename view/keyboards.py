from __future__ import annotations

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

BTN_STATUS = "Статус"

CB_PUBLISH_TELEGRAM = "story:publish:telegram"
CB_PUBLISH_MAX = "story:publish:max"
CB_PUBLISH_WHATSAPP = "story:publish:whatsapp"
CB_PUBLISH_VK = "story:publish:vk"
CB_PUBLISH_INSTAGRAM = "story:publish:instagram"
CB_PUBLISH_BOTH = "story:publish:both"
CB_PUBLISH_ALL = "story:publish:all"
CB_PUBLISH_NO = "story:no"
CB_ADD_TEXT = "story:add_text"
CB_EDIT_TEXT = "story:edit_text"
CB_REMOVE_TEXT = "story:remove_text"
CB_MAX_AUTH_CANCEL = "max_auth:cancel"
CB_MAX_AUTH_QR = "max_auth:qr"
CB_MAX_AUTH_SMS = "max_auth:sms"
CB_MAX_AUTH_RESEND = "max_auth:resend"
CB_MAX_AUTH_CALL = "max_auth:call"


def main_keyboard() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton(BTN_STATUS))
    return markup


def phone_keyboard() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Отправить номер", request_contact=True))
    return markup


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def max_code_retry_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Ещё раз SMS", callback_data=CB_MAX_AUTH_RESEND),
        InlineKeyboardButton("Позвонить", callback_data=CB_MAX_AUTH_CALL),
    )
    return markup


def max_auth_method_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Войти по QR", callback_data=CB_MAX_AUTH_QR),
        InlineKeyboardButton("Войти по SMS", callback_data=CB_MAX_AUTH_SMS),
    )
    markup.row(
        InlineKeyboardButton("Отменить", callback_data=CB_MAX_AUTH_CANCEL),
    )
    return markup


def _publish_rows(markup: InlineKeyboardMarkup) -> None:
    markup.row(
        InlineKeyboardButton("Telegram", callback_data=CB_PUBLISH_TELEGRAM),
        InlineKeyboardButton("MAX", callback_data=CB_PUBLISH_MAX),
        InlineKeyboardButton("WhatsApp", callback_data=CB_PUBLISH_WHATSAPP),
    )
    markup.row(
        InlineKeyboardButton("VK", callback_data=CB_PUBLISH_VK),
        InlineKeyboardButton("Instagram", callback_data=CB_PUBLISH_INSTAGRAM),
        InlineKeyboardButton("Все", callback_data=CB_PUBLISH_ALL),
    )


def publish_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    _publish_rows(markup)
    markup.row(
        InlineKeyboardButton("Добавить текст", callback_data=CB_ADD_TEXT),
        InlineKeyboardButton("Отменить", callback_data=CB_PUBLISH_NO),
    )
    return markup


def preview_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    _publish_rows(markup)
    markup.row(
        InlineKeyboardButton("Изменить текст", callback_data=CB_EDIT_TEXT),
        InlineKeyboardButton("Убрать текст", callback_data=CB_REMOVE_TEXT),
        InlineKeyboardButton("Отменить", callback_data=CB_PUBLISH_NO),
    )
    return markup
