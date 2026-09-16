from __future__ import annotations

from config import business_connection_id
from controller.helpers import (
    reject_if_not_private,
    telegram_id_of,
)
from model.pending import set_pending
from view import MSG_ASK_PUBLISH, MSG_BUSINESS_CONNECTION_MISSING, publish_keyboard


def register_photo_handlers(bot):
    @bot.message_handler(content_types=["photo"])
    def handle_photo(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        if business_connection_id() is None:
            bot.send_message(message.chat.id, MSG_BUSINESS_CONNECTION_MISSING)
            return
        photos = getattr(message, "photo", None) or []
        if not photos:
            return
        file_id = photos[-1].file_id
        set_pending(telegram_id, file_id)
        bot.send_message(
            message.chat.id,
            MSG_ASK_PUBLISH,
            reply_markup=publish_keyboard(),
        )
