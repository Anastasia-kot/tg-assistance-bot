from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from model.stories import user_lock
from model.vk_stories import VkSessionRequired, refresh_vk_profile

logger = logging.getLogger("vk_flood_check")

FLOOD_CHECK_STEP_MINUTES = 5
MAX_FLOOD_CHECKS = 12


@dataclass
class VkFloodCheckJob:
    telegram_id: int
    chat_id: int
    attempt: int
    timer: threading.Timer


_lock = threading.Lock()
_jobs: dict[int, VkFloodCheckJob] = {}


def flood_check_delay_minutes(attempt: int) -> int:
    return FLOOD_CHECK_STEP_MINUTES * max(1, int(attempt))


def has_vk_flood_check(telegram_id: int) -> bool:
    with _lock:
        return int(telegram_id) in _jobs


def cancel_vk_flood_check(telegram_id: int) -> bool:
    with _lock:
        job = _jobs.pop(int(telegram_id), None)
    if job is None:
        return False
    job.timer.cancel()
    logger.info("VK flood check cancelled: telegram_id=%s", telegram_id)
    return True


def schedule_vk_flood_check(
    bot,
    telegram_id: int,
    chat_id: int,
    attempt: int,
) -> int | None:
    """Schedule next availability probe. Returns delay minutes or None if capped."""
    if attempt < 1 or attempt > MAX_FLOOD_CHECKS:
        return None
    cancel_vk_flood_check(telegram_id)
    delay_minutes = flood_check_delay_minutes(attempt)
    timer = threading.Timer(
        delay_minutes * 60,
        _run_vk_flood_check,
        args=(bot, int(telegram_id), int(chat_id), attempt),
    )
    timer.daemon = True
    job = VkFloodCheckJob(
        telegram_id=int(telegram_id),
        chat_id=int(chat_id),
        attempt=attempt,
        timer=timer,
    )
    with _lock:
        _jobs[int(telegram_id)] = job
    timer.start()
    logger.info(
        "VK flood check scheduled: telegram_id=%s attempt=%s delay=%smin",
        telegram_id,
        attempt,
        delay_minutes,
    )
    return delay_minutes


def _clear_job(telegram_id: int, expected_attempt: int) -> bool:
    with _lock:
        job = _jobs.get(int(telegram_id))
        if job is None or job.attempt != expected_attempt:
            return False
        _jobs.pop(int(telegram_id), None)
        return True


def _run_vk_flood_check(bot, telegram_id: int, chat_id: int, attempt: int) -> None:
    if not _clear_job(telegram_id, attempt):
        return
    from view import (
        MSG_VK_FLOOD_CHECK_EXHAUSTED,
        MSG_VK_FLOOD_CHECK_FAILED,
        MSG_VK_FLOOD_CHECK_OK,
        MSG_VK_FLOOD_CHECK_SCHEDULED,
        vk_flood_check_cancel_keyboard,
    )

    try:
        with user_lock(telegram_id):
            result = refresh_vk_profile(telegram_id)
    except VkSessionRequired as error:
        bot.send_message(chat_id, error.user_message)
        return
    except Exception:
        logger.exception("VK flood check crashed: telegram_id=%s", telegram_id)
        bot.send_message(chat_id, MSG_VK_FLOOD_CHECK_FAILED.format(error="внутренняя ошибка"))
        return

    if result["ok"]:
        name = result.get("name") or "VK"
        bot.send_message(
            chat_id,
            MSG_VK_FLOOD_CHECK_OK.format(name=name, attempt=attempt),
        )
        return

    error_text = result.get("error") or "VK недоступен"
    if not result.get("retryable"):
        bot.send_message(
            chat_id,
            MSG_VK_FLOOD_CHECK_FAILED.format(error=error_text),
        )
        return

    next_attempt = attempt + 1
    delay = schedule_vk_flood_check(bot, telegram_id, chat_id, next_attempt)
    if delay is None:
        bot.send_message(
            chat_id,
            MSG_VK_FLOOD_CHECK_EXHAUSTED.format(
                attempt=attempt,
                error=error_text,
            ),
        )
        return
    bot.send_message(
        chat_id,
        MSG_VK_FLOOD_CHECK_SCHEDULED.format(
            minutes=delay,
            attempt=next_attempt,
            max_attempts=MAX_FLOOD_CHECKS,
            error=error_text,
        ),
        reply_markup=vk_flood_check_cancel_keyboard(),
    )
