from __future__ import annotations

from controller.helpers import (
    prompt_finish_auth,
    reject_if_not_private,
    telegram_id_of,
)
from model.pending import set_pending
from model.users import ensure_user, is_ready
from view import MSG_ASK_PUBLISH, publish_keyboard


def register_photo_handlers(bot):
    @bot.message_handler(content_types=["photo"])
    def handle_photo(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        user = ensure_user(telegram_id)
        if not is_ready(user):
            prompt_finish_auth(bot, message.chat.id, user)
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
