from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Optional

from model.stories import user_lock
from model.vk_stories import (
    VkSessionRequired,
    VkStoriesError,
    check_vk_token,
    publish_vk_photo,
)

logger = logging.getLogger("vk_retry")

RETRY_DELAY_SECONDS = 300
MAX_ATTEMPTS = 3


@dataclass
class VkRetryJob:
    telegram_id: int
    chat_id: int
    file_id: str
    caption: Optional[str]
    attempt: int
    timer: threading.Timer


_lock = threading.Lock()
_jobs: dict[int, VkRetryJob] = {}


def has_vk_retry(telegram_id: int) -> bool:
    with _lock:
        return int(telegram_id) in _jobs


def cancel_vk_retry(telegram_id: int) -> bool:
    with _lock:
        job = _jobs.pop(int(telegram_id), None)
    if job is None:
        return False
    job.timer.cancel()
    logger.info("VK retry cancelled: telegram_id=%s", telegram_id)
    return True


def schedule_vk_retry(
    bot,
    telegram_id: int,
    chat_id: int,
    file_id: str,
    caption: str | None,
    attempt: int,
) -> bool:
    if attempt > MAX_ATTEMPTS:
        return False
    cancel_vk_retry(telegram_id)
    timer = threading.Timer(
        RETRY_DELAY_SECONDS,
        _run_vk_retry,
        args=(bot, int(telegram_id), int(chat_id), file_id, caption, attempt),
    )
    timer.daemon = True
    job = VkRetryJob(
        telegram_id=int(telegram_id),
        chat_id=int(chat_id),
        file_id=file_id,
        caption=caption,
        attempt=attempt,
        timer=timer,
    )
    with _lock:
        _jobs[int(telegram_id)] = job
    timer.start()
    logger.info(
        "VK retry scheduled: telegram_id=%s attempt=%s delay=%ss",
        telegram_id,
        attempt,
        RETRY_DELAY_SECONDS,
    )
    return True


def _clear_job(telegram_id: int, expected_attempt: int) -> bool:
    with _lock:
        job = _jobs.get(int(telegram_id))
        if job is None or job.attempt != expected_attempt:
            return False
        _jobs.pop(int(telegram_id), None)
        return True


def _run_vk_retry(
    bot,
    telegram_id: int,
    chat_id: int,
    file_id: str,
    caption: str | None,
    attempt: int,
) -> None:
    if not _clear_job(telegram_id, attempt):
        return
    from view import MSG_PUBLISHED, MSG_VK_RETRY_SCHEDULED, vk_retry_cancel_keyboard

    try:
        with user_lock(telegram_id):
            status = check_vk_token(telegram_id)
            if not status["ok"]:
                raise VkStoriesError(
                    status["error"] or "Проверка токена VK не прошла.",
                    retryable=bool(status.get("retryable")),
                )
            file_info = bot.get_file(file_id)
            image_bytes = bot.download_file(file_info.file_path)
            publish_vk_photo(telegram_id, image_bytes, caption)
        bot.send_message(
            chat_id,
            MSG_PUBLISHED.format(platforms="VK"),
        )
        bot.send_photo(chat_id, file_id, caption=caption)
    except VkSessionRequired as error:
        bot.send_message(chat_id, error.user_message)
    except VkStoriesError as error:
        logger.warning(
            "VK retry failed: telegram_id=%s attempt=%s retryable=%s",
            telegram_id,
            attempt,
            error.retryable,
        )
        next_attempt = attempt + 1
        if error.retryable and schedule_vk_retry(
            bot,
            telegram_id,
            chat_id,
            file_id,
            caption,
            next_attempt,
        ):
            bot.send_message(
                chat_id,
                MSG_VK_RETRY_SCHEDULED.format(
                    minutes=RETRY_DELAY_SECONDS // 60,
                    attempt=next_attempt,
                    max_attempts=MAX_ATTEMPTS,
                    error=error.user_message,
                ),
                reply_markup=vk_retry_cancel_keyboard(),
            )
            return
        bot.send_message(chat_id, error.user_message)
    except Exception:
        logger.exception("VK retry crashed: telegram_id=%s", telegram_id)
        bot.send_message(
            chat_id,
            "Повтор публикации во VK не удался из-за внутренней ошибки.",
        )
