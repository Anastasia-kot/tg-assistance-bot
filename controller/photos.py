from __future__ import annotations

from controller.helpers import (
    reject_if_not_private,
    telegram_id_of,
)
from model.pending import is_waiting_for_caption, set_caption, set_pending
from view import (
    BTN_STATUS,
    MSG_ASK_CAPTION,
    MSG_ASK_PUBLISH,
    MSG_CAPTION_TOO_LONG,
    preview_keyboard,
    publish_keyboard,
)

MAX_PREVIEW_CAPTION_LENGTH = 1024


def _is_caption_message(message) -> bool:
    telegram_id = telegram_id_of(message)
    return bool(
        telegram_id is not None
        and getattr(message, "text", None)
        and message.text.strip() != BTN_STATUS
        and not message.text.startswith("/")
        and is_waiting_for_caption(telegram_id)
    )


def register_photo_handlers(bot):
    @bot.message_handler(content_types=["photo"])
    def handle_photo(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        photos = getattr(message, "photo", None) or []
        if not photos:
            return
        file_id = photos[-1].file_id
        caption = (getattr(message, "caption", None) or "").strip()
        if caption:
            set_pending(telegram_id, file_id, caption=caption)
            bot.send_photo(
                message.chat.id,
                file_id,
                caption=caption,
                reply_markup=preview_keyboard(),
            )
            return
        set_pending(telegram_id, file_id)
        bot.send_message(
            message.chat.id,
            MSG_ASK_PUBLISH,
            reply_markup=publish_keyboard(),
        )

    @bot.message_handler(func=_is_caption_message, content_types=["text"])
    def handle_caption(message):
        if reject_if_not_private(bot, message):
            return
        telegram_id = telegram_id_of(message)
        if telegram_id is None:
            return
        caption = (message.text or "").strip()
        if not caption:
            bot.send_message(message.chat.id, MSG_ASK_CAPTION)
            return
        if len(caption) > MAX_PREVIEW_CAPTION_LENGTH:
            bot.send_message(
                message.chat.id,
                MSG_CAPTION_TOO_LONG.format(limit=MAX_PREVIEW_CAPTION_LENGTH),
            )
            return
        story = set_caption(telegram_id, caption)
        if story is None:
            return
        bot.send_photo(
            message.chat.id,
            story.file_id,
            caption=story.caption,
            reply_markup=preview_keyboard(),
        )
