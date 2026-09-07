from __future__ import annotations

import logging

from controller.helpers import telegram_id_of
from model.pending import pop_pending
from model.stories import SessionExpiredError, StoriesError, publish_photo, user_lock
from model.users import ensure_user, is_ready, reset_login, save_session
from view import (
    CB_PUBLISH_NO,
    CB_PUBLISH_YES,
    MSG_ASK_PHONE,
    MSG_CANCELLED,
    MSG_NO_PENDING,
    MSG_PUBLISHED,
    phone_keyboard,
)

logger = logging.getLogger("controller.callbacks")


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
            user = ensure_user(telegram_id)
            if not is_ready(user):
                bot.answer_callback_query(call.id, text="Сначала подключите аккаунт.")
                _edit(bot, call, "Сначала подключите аккаунт.")
                return
            file_id = pop_pending(telegram_id)
            if not file_id:
                bot.answer_callback_query(call.id, text=MSG_NO_PENDING)
                _edit(bot, call, MSG_NO_PENDING)
                return
            try:
                file_info = bot.get_file(file_id)
                image_bytes = bot.download_file(file_info.file_path)
                new_session = publish_photo(user["session_string"], image_bytes)
                save_session(telegram_id, new_session)
            except SessionExpiredError as exc:
                reset_login(telegram_id, keep_phone=True)
                bot.answer_callback_query(call.id, text="Сессия истекла")
                _edit(bot, call, exc.user_message)
                bot.send_message(
                    call.message.chat.id,
                    MSG_ASK_PHONE,
                    reply_markup=phone_keyboard(),
                )
                return
            except StoriesError as exc:
                saved = getattr(exc, "session_string", None)
                if saved:
                    save_session(telegram_id, saved)
                logger.warning("publish failed for %s: %s", telegram_id, exc.user_message)
                bot.answer_callback_query(call.id, text="Не удалось опубликовать")
                _edit(bot, call, exc.user_message)
                return
            except Exception:
                logger.exception("publish failed for %s", telegram_id)
                bot.answer_callback_query(call.id, text="Ошибка публикации")
                _edit(bot, call, "Не удалось опубликовать сторис. Попробуйте ещё раз.")
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
