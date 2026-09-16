from __future__ import annotations

import io
import logging

from telebot import types
from telebot.apihelper import ApiTelegramException

from config import business_connection_id
from controller.helpers import telegram_id_of
from model.pending import pop_pending
from model.stories import STORY_PERIOD_SECONDS, user_lock
from view import (
    CB_PUBLISH_NO,
    CB_PUBLISH_YES,
    MSG_BUSINESS_CONNECTION_MISSING,
    MSG_CANCELLED,
    MSG_NO_PENDING,
    MSG_PUBLISHED,
)

logger = logging.getLogger("controller.callbacks")


def _telegram_error_message(error: ApiTelegramException) -> str:
    if error.description == "Bad Request: BOT_ACCESS_FORBIDDEN":
        return (
            "Telegram запретил публикацию: бизнес-подключение отключено "
            "или у бота нет права публиковать истории."
        )
    return (
        f"Telegram отклонил публикацию: {error.description} "
        f"(код {error.error_code})."
    )


def _publish_business_photo(bot, connection_id: str, image_bytes: bytes) -> None:
    photo = types.InputFile(io.BytesIO(image_bytes), file_name="story.jpg")
    content = types.InputStoryContentPhoto(photo=photo)
    bot.post_story(
        business_connection_id=connection_id,
        content=content,
        active_period=STORY_PERIOD_SECONDS,
    )


def _edit(bot, call, text: str, reply_markup=None) -> None:
    msg = call.message
    try:
        bot.edit_message_text(
            text,
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            reply_markup=reply_markup,
        )
    except Exception:
        bot.send_message(msg.chat.id, text, reply_markup=reply_markup)


def register_callback_handlers(bot):
    @bot.callback_query_handler(func=lambda call: call.data == CB_PUBLISH_YES)
    def handle_yes(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        with user_lock(telegram_id):
            connection_id = business_connection_id()
            if connection_id is None:
                bot.answer_callback_query(call.id, text="Ошибка конфигурации")
                _edit(bot, call, MSG_BUSINESS_CONNECTION_MISSING)
                return
            file_id = pop_pending(telegram_id)
            if not file_id:
                bot.answer_callback_query(call.id, text=MSG_NO_PENDING)
                _edit(bot, call, MSG_NO_PENDING)
                return
            try:
                file_info = bot.get_file(file_id)
                image_bytes = bot.download_file(file_info.file_path)
                _publish_business_photo(bot, connection_id, image_bytes)
            except ApiTelegramException as error:
                logger.error(
                    "story publish rejected: telegram_id=%s, "
                    "business_connection_id_suffix=%s, error_code=%s, description=%s",
                    telegram_id,
                    connection_id[-6:],
                    error.error_code,
                    error.description,
                )
                bot.answer_callback_query(call.id, text="Telegram отклонил публикацию")
                _edit(bot, call, _telegram_error_message(error))
                return
            except Exception:
                logger.exception(
                    "story publish failed: telegram_id=%s, "
                    "business_connection_id_suffix=%s",
                    telegram_id,
                    connection_id[-6:],
                )
                bot.answer_callback_query(call.id, text="Ошибка публикации")
                _edit(
                    bot,
                    call,
                    "Не удалось опубликовать сторис из-за внутренней ошибки. "
                    "Подробности записаны в журнал.",
                )
                return
        bot.answer_callback_query(call.id, text="Опубликовано")
        _edit(bot, call, MSG_PUBLISHED)

    @bot.callback_query_handler(func=lambda call: call.data == CB_PUBLISH_NO)
    def handle_no(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        pop_pending(telegram_id)
        bot.answer_callback_query(call.id, text="Отменено")
        _edit(bot, call, MSG_CANCELLED)
