from __future__ import annotations

import io
import logging

from telebot import types
from telebot.apihelper import ApiTelegramException

from config import business_connection_id
from controller.helpers import telegram_id_of
from model.pending import (
    clear_pending,
    get_pending,
    toggle_pending_target,
    wait_for_caption,
)
from model.platforms import (
    PLATFORM_TITLES,
    PLATFORM_VK,
    connected_platform_keys,
)
from model.stories import STORY_PERIOD_SECONDS, user_lock
from model.vk_retry import (
    MAX_ATTEMPTS,
    RETRY_DELAY_SECONDS,
    cancel_vk_retry,
    schedule_vk_retry,
)
from model.vk_stories import VkSessionRequired, VkStoriesError, publish_vk_photo
from view import (
    CB_ADD_TEXT,
    CB_EDIT_TEXT,
    CB_PUBLISH_GO,
    CB_PUBLISH_NO,
    CB_VK_RETRY_CANCEL,
    MSG_ASK_CAPTION,
    MSG_BUSINESS_CONNECTION_MISSING,
    MSG_CANCELLED,
    MSG_NO_PENDING,
    MSG_PLATFORM_LOCKED,
    MSG_PUBLISH_NEED_TARGET,
    MSG_PUBLISHED,
    MSG_VK_RETRY_CANCELLED,
    MSG_VK_RETRY_SCHEDULED,
    MSG_VK_STORY_NEEDS_LOGIN,
    is_locked_callback,
    is_toggle_callback,
    locked_platform_from_callback,
    preview_keyboard,
    publish_keyboard,
    toggle_platform_from_callback,
    vk_retry_cancel_keyboard,
)

logger = logging.getLogger("controller.callbacks")

TARGET_NAMES = dict(PLATFORM_TITLES)


def _story_keyboard(telegram_id: int, caption: str | None):
    connected = connected_platform_keys(telegram_id)
    story = get_pending(telegram_id)
    if caption:
        return preview_keyboard(story, connected)
    return publish_keyboard(story, connected)


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
    if target == PLATFORM_VK:
        publish_vk_photo(telegram_id, image_bytes, caption)
        return
    connection_id = business_connection_id()
    if connection_id is None:
        raise VkStoriesError(MSG_BUSINESS_CONNECTION_MISSING)
    _publish_business_photo(bot, connection_id, image_bytes, caption)


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

    @bot.callback_query_handler(func=lambda call: is_toggle_callback(call.data))
    def handle_toggle(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        platform = toggle_platform_from_callback(call.data)
        connected = connected_platform_keys(telegram_id)
        story = toggle_pending_target(telegram_id, platform, allowed=connected)
        if story is None:
            bot.answer_callback_query(call.id, text=MSG_NO_PENDING)
            return
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_story_keyboard(telegram_id, story.caption),
            )
        except Exception:
            logger.debug("could not refresh publish checklist", exc_info=True)

    @bot.callback_query_handler(func=lambda call: is_locked_callback(call.data))
    def handle_locked(call):
        platform = locked_platform_from_callback(call.data)
        title = PLATFORM_TITLES.get(platform, platform)
        bot.answer_callback_query(
            call.id,
            text=MSG_PLATFORM_LOCKED.format(title=title),
            show_alert=True,
        )

    @bot.callback_query_handler(func=lambda call: call.data == CB_PUBLISH_GO)
    def handle_publish(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        story = get_pending(telegram_id)
        if story is None:
            bot.answer_callback_query(call.id, text=MSG_NO_PENDING)
            _edit(bot, call, MSG_NO_PENDING)
            return
        connected = connected_platform_keys(telegram_id)
        targets = [key for key in story.selected if key in connected]
        if not targets:
            bot.answer_callback_query(
                call.id,
                text=MSG_PUBLISH_NEED_TARGET,
                show_alert=True,
            )
            return
        bot.answer_callback_query(call.id, text="Публикую…")
        with user_lock(telegram_id):
            story = get_pending(telegram_id)
            if story is None:
                _edit(bot, call, MSG_NO_PENDING)
                return
            try:
                file_info = bot.get_file(story.file_id)
                image_bytes = bot.download_file(file_info.file_path)
            except Exception:
                logger.exception(
                    "story download failed: telegram_id=%s",
                    telegram_id,
                )
                _edit(
                    bot,
                    call,
                    "Не удалось скачать фото для публикации. Пришлите картинку ещё раз.",
                    reply_markup=_story_keyboard(telegram_id, story.caption),
                )
                return
            published = []
            for target in targets:
                try:
                    _publish_target(
                        bot,
                        target,
                        telegram_id,
                        image_bytes,
                        story.caption,
                    )
                    published.append(TARGET_NAMES[target])
                except VkSessionRequired:
                    bot.send_message(call.message.chat.id, MSG_VK_STORY_NEEDS_LOGIN)
                except ApiTelegramException as error:
                    logger.error(
                        "story publish rejected: telegram_id=%s, target=%s, "
                        "error_code=%s, description=%s",
                        telegram_id,
                        target,
                        error.error_code,
                        error.description,
                    )
                    _edit(
                        bot,
                        call,
                        _telegram_error_message(error),
                        reply_markup=_story_keyboard(telegram_id, story.caption),
                    )
                    return
                except VkStoriesError as error:
                    if target == PLATFORM_VK and error.retryable:
                        scheduled = schedule_vk_retry(
                            bot,
                            telegram_id,
                            call.message.chat.id,
                            story.file_id,
                            story.caption,
                            1,
                        )
                        if scheduled:
                            bot.send_message(
                                call.message.chat.id,
                                MSG_VK_RETRY_SCHEDULED.format(
                                    minutes=RETRY_DELAY_SECONDS // 60,
                                    attempt=1,
                                    max_attempts=MAX_ATTEMPTS,
                                    error=error.user_message,
                                ),
                                reply_markup=vk_retry_cancel_keyboard(),
                            )
                            continue
                    _edit(
                        bot,
                        call,
                        error.user_message,
                        reply_markup=_story_keyboard(telegram_id, story.caption),
                    )
                    return
                except Exception:
                    logger.exception(
                        "story publish failed: telegram_id=%s, target=%s",
                        telegram_id,
                        target,
                    )
                    _edit(
                        bot,
                        call,
                        "Не удалось опубликовать сторис из-за внутренней ошибки. "
                        "Подробности записаны в журнал.",
                        reply_markup=_story_keyboard(telegram_id, story.caption),
                    )
                    return
            if not published:
                return
            clear_pending(telegram_id)
        _remove_inline_keyboard(bot, call)
        try:
            bot.send_message(
                call.message.chat.id,
                MSG_PUBLISHED.format(platforms="\n".join(published)),
            )
            bot.send_photo(
                call.message.chat.id,
                story.file_id,
                caption=story.caption,
            )
        except Exception:
            logger.exception(
                "story publish report failed: telegram_id=%s",
                telegram_id,
            )

    @bot.callback_query_handler(func=lambda call: call.data == CB_PUBLISH_NO)
    def handle_no(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        clear_pending(telegram_id)
        cancel_vk_retry(telegram_id)
        bot.answer_callback_query(call.id, text="Отменено")
        _edit(bot, call, MSG_CANCELLED)

    @bot.callback_query_handler(func=lambda call: call.data == CB_VK_RETRY_CANCEL)
    def handle_vk_retry_cancel(call):
        telegram_id = telegram_id_of(call)
        if telegram_id is None:
            bot.answer_callback_query(call.id)
            return
        cancelled = cancel_vk_retry(telegram_id)
        bot.answer_callback_query(
            call.id,
            text="Отменено" if cancelled else "Повтора нет",
        )
        _edit(
            bot,
            call,
            MSG_VK_RETRY_CANCELLED if cancelled else "Автоповтор VK уже не запланирован.",
        )
