from __future__ import annotations

import io
import logging

from telebot import types
from telebot.apihelper import ApiTelegramException

from config import business_connection_id
from controller.helpers import telegram_id_of
from model.ig_stories import publish_ig_photo
from model.locks import user_lock
from model.max_stories import (
    MaxSessionRequired,
    MaxStoriesError,
    publish_max_photo,
)
from model.pending import (
    clear_pending,
    get_pending,
    mark_target_published,
    remove_caption,
    wait_for_caption,
)
from model.platform_errors import PlatformSessionRequired, PlatformStoriesError
from model.vk_stories import publish_vk_photo
from model.wa_stories import publish_wa_photo
from view import (
    CB_ADD_TEXT,
    CB_EDIT_TEXT,
    CB_PUBLISH_ALL,
    CB_PUBLISH_BOTH,
    CB_PUBLISH_INSTAGRAM,
    CB_PUBLISH_MAX,
    CB_PUBLISH_NO,
    CB_PUBLISH_TELEGRAM,
    CB_PUBLISH_VK,
    CB_PUBLISH_WHATSAPP,
    CB_REMOVE_TEXT,
    MSG_ASK_CAPTION,
    MSG_BUSINESS_CONNECTION_MISSING,
    MSG_CANCELLED,
    MSG_IG_STORY_NEEDS_LOGIN,
    MSG_MAX_STORY_NEEDS_LOGIN,
    MSG_NO_PENDING,
    MSG_PUBLISHED,
    MSG_VK_STORY_NEEDS_LOGIN,
    MSG_WA_STORY_NEEDS_LOGIN,
    preview_keyboard,
    publish_keyboard,
)

logger = logging.getLogger("controller.callbacks")

STORY_PERIOD_SECONDS = 86400
TARGET_TELEGRAM = "telegram"
TARGET_MAX = "max"
TARGET_WHATSAPP = "whatsapp"
TARGET_VK = "vk"
TARGET_INSTAGRAM = "instagram"
ALL_TARGETS = (
    TARGET_TELEGRAM,
    TARGET_MAX,
    TARGET_WHATSAPP,
    TARGET_VK,
    TARGET_INSTAGRAM,
)
PUBLISH_TARGETS = {
    CB_PUBLISH_TELEGRAM: frozenset({TARGET_TELEGRAM}),
    CB_PUBLISH_MAX: frozenset({TARGET_MAX}),
    CB_PUBLISH_WHATSAPP: frozenset({TARGET_WHATSAPP}),
    CB_PUBLISH_VK: frozenset({TARGET_VK}),
    CB_PUBLISH_INSTAGRAM: frozenset({TARGET_INSTAGRAM}),
    CB_PUBLISH_BOTH: frozenset({TARGET_TELEGRAM, TARGET_MAX}),
    CB_PUBLISH_ALL: frozenset(ALL_TARGETS),
}
TARGET_NAMES = {
    TARGET_TELEGRAM: "Telegram",
    TARGET_MAX: "MAX",
    TARGET_WHATSAPP: "WhatsApp",
    TARGET_VK: "VK",
    TARGET_INSTAGRAM: "Instagram",
}
LOGIN_MESSAGES = {
    TARGET_MAX: MSG_MAX_STORY_NEEDS_LOGIN,
    TARGET_WHATSAPP: MSG_WA_STORY_NEEDS_LOGIN,
    TARGET_VK: MSG_VK_STORY_NEEDS_LOGIN,
    TARGET_INSTAGRAM: MSG_IG_STORY_NEEDS_LOGIN,
}


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


def _publish_business_photo(
    bot,
    connection_id: str,
    image_bytes: bytes,
    caption: str | None,
) -> None:
    photo = types.InputFile(io.BytesIO(image_bytes), file_name="story.jpg")
    content = types.InputStoryContentPhoto(photo=photo)
    bot.post_story(
        business_connection_id=connection_id,
        content=content,
        active_period=STORY_PERIOD_SECONDS,
        caption=caption,
    )


def _publish_target(
    bot,
    target: str,
    telegram_id: int,
    image_bytes: bytes,
    caption: str | None,
) -> None:
    if target == TARGET_TELEGRAM:
        connection_id = business_connection_id()
        if connection_id is None:
            raise PlatformStoriesError(MSG_BUSINESS_CONNECTION_MISSING)
        _publish_business_photo(bot, connection_id, image_bytes, caption)
        return
    if target == TARGET_MAX:
        publish_max_photo(telegram_id, image_bytes, caption)
        return
    if target == TARGET_WHATSAPP:
        publish_wa_photo(telegram_id, image_bytes, caption)
        return
    if target == TARGET_VK:
        publish_vk_photo(telegram_id, image_bytes, caption)
        return
    publish_ig_photo(telegram_id, image_bytes, caption)


def _edit(bot, call, text: str, reply_markup=None) -> None:
    msg = call.message
    try:
        if getattr(msg, "content_type", None) == "photo":
            bot.edit_message_caption(
                caption=text,
                chat_id=msg.chat.id,
                message_id=msg.message_id,
                reply_markup=reply_markup,
            )
            return
        bot.edit_message_text(
            text,
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            reply_markup=reply_markup,
        )
    except Exception:
        bot.send_message(msg.chat.id, text, reply_markup=reply_markup)


def _remove_inline_keyboard(bot, call) -> None:
    try:
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
    except Exception:
        logger.debug("could not remove story keyboard", exc_info=True)


def _story_keyboard(caption: str | None):
    return preview_keyboard() if caption else publish_keyboard()


def _send_publish_report(bot, call, story, targets: frozenset[str]) -> None:
    platforms = ", ".join(
        TARGET_NAMES[target]
        for target in ALL_TARGETS
        if target in targets
    )
    try:
        bot.send_message(
            call.message.chat.id,
            MSG_PUBLISHED.format(platforms=platforms),
        )
        bot.send_photo(
            call.message.chat.id,
            story.file_id,
            caption=story.caption,
        )
    except Exception:
        logger.exception(
            "story publish report failed: telegram_id=%s",
            telegram_id_of(call),
        )


def _answer(bot, call, text: str | None = None) -> None:
    try:
        bot.answer_callback_query(call.id, text=text)
    except Exception:
        logger.debug("could not answer callback", exc_info=True)


def register_callback_handlers(bot):
    @bot.callback_query_handler(
        func=lambda call: call.data in {CB_ADD_TEXT, CB_EDIT_TEXT}
    )
    def handle_caption_request(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        story = wait_for_caption(telegram_id)
        if story is None:
            bot.answer_callback_query(call.id, text=MSG_NO_PENDING)
            _edit(bot, call, MSG_NO_PENDING)
            return
        _remove_inline_keyboard(bot, call)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, MSG_ASK_CAPTION)

    @bot.callback_query_handler(func=lambda call: call.data == CB_REMOVE_TEXT)
    def handle_caption_remove(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        story = remove_caption(telegram_id)
        if story is None:
            bot.answer_callback_query(call.id, text=MSG_NO_PENDING)
            _edit(bot, call, MSG_NO_PENDING)
            return
        bot.answer_callback_query(call.id, text="Текст удалён")
        try:
            bot.edit_message_caption(
                caption=None,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=publish_keyboard(),
            )
        except Exception:
            logger.debug("could not update story preview", exc_info=True)
            bot.send_photo(
                call.message.chat.id,
                story.file_id,
                reply_markup=publish_keyboard(),
            )

    @bot.callback_query_handler(func=lambda call: call.data in PUBLISH_TARGETS)
    def handle_publish(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        requested_targets = PUBLISH_TARGETS[call.data]
        with user_lock(telegram_id):
            story = get_pending(telegram_id)
            if story is None:
                bot.answer_callback_query(call.id, text=MSG_NO_PENDING)
                _edit(bot, call, MSG_NO_PENDING)
                return
            remaining_targets = requested_targets - story.published_targets
            if not remaining_targets:
                _answer(bot, call, "Уже опубликовано")
                return
            _answer(bot, call, "Публикую…")
            try:
                file_info = bot.get_file(story.file_id)
                image_bytes = bot.download_file(file_info.file_path)
            except Exception:
                logger.exception(
                    "story media download failed: telegram_id=%s",
                    telegram_id,
                )
                _edit(
                    bot,
                    call,
                    "Не удалось скачать фотографию для публикации.",
                    reply_markup=_story_keyboard(story.caption),
                )
                return

            errors: dict[str, str] = {}
            for target in ALL_TARGETS:
                if target not in remaining_targets:
                    continue
                try:
                    _publish_target(
                        bot,
                        target,
                        telegram_id,
                        image_bytes,
                        story.caption,
                    )
                except ApiTelegramException as error:
                    logger.error(
                        "Telegram story rejected: telegram_id=%s, "
                        "error_code=%s, description=%s",
                        telegram_id,
                        error.error_code,
                        error.description,
                    )
                    errors[target] = _telegram_error_message(error)
                    continue
                except (MaxSessionRequired, PlatformSessionRequired):
                    errors[target] = LOGIN_MESSAGES.get(
                        target,
                        "Сначала подключите аккаунт.",
                    )
                    continue
                except (MaxStoriesError, PlatformStoriesError) as error:
                    logger.error(
                        "%s story rejected: telegram_id=%s, reason=%s",
                        TARGET_NAMES[target],
                        telegram_id,
                        error,
                    )
                    errors[target] = error.user_message
                    continue
                except Exception:
                    logger.exception(
                        "%s story publish failed: telegram_id=%s",
                        TARGET_NAMES[target],
                        telegram_id,
                    )
                    errors[target] = (
                        f"Внутренняя ошибка публикации в {TARGET_NAMES[target]}."
                    )
                    continue
                updated = mark_target_published(telegram_id, target)
                if updated is not None:
                    story = updated

            is_complete = requested_targets.issubset(story.published_targets)
            if is_complete:
                clear_pending(telegram_id)

        if is_complete:
            try:
                _remove_inline_keyboard(bot, call)
                _send_publish_report(bot, call, story, requested_targets)
            except Exception:
                logger.exception(
                    "story publish report failed: telegram_id=%s",
                    telegram_id,
                )
            return

        result_lines = []
        for target in ALL_TARGETS:
            if target not in requested_targets:
                continue
            if target in story.published_targets:
                result_lines.append(f"{TARGET_NAMES[target]}: опубликовано.")
                continue
            result_lines.append(
                f"{TARGET_NAMES[target]}: "
                f"{errors.get(target, 'не удалось опубликовать.')}"
            )
        _edit(
            bot,
            call,
            "\n\n".join(result_lines),
            reply_markup=_story_keyboard(story.caption),
        )

    @bot.callback_query_handler(func=lambda call: call.data == CB_PUBLISH_NO)
    def handle_no(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        clear_pending(telegram_id)
        bot.answer_callback_query(call.id, text="Отменено")
        _edit(bot, call, MSG_CANCELLED)
