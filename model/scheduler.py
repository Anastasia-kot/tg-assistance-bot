import logging
import threading
import time

import schedule

from model.notifications import (
    notify_today_tasks,
    notify_tomorrow_tasks,
    set_notifications_bot,
)
from model.tasks import archive_completed_tasks


logger = logging.getLogger(__name__)

_scheduler_started = False
_scheduler_lock = threading.Lock()


def notifications_scheduler(bot) -> None:
    set_notifications_bot(bot)
    schedule.every().day.at("07:00").do(notify_today_tasks)
    schedule.every().day.at("22:00").do(notify_tomorrow_tasks)


def archive_completed_tasks_scheduler() -> None:
    schedule.every().day.at("00:00").do(_archive_completed_tasks)


def start_scheduler(bot) -> None:
    global _scheduler_started
    with _scheduler_lock:
        if _scheduler_started:
            logger.info("scheduler: already started")
            return

        notifications_scheduler(bot)
        archive_completed_tasks_scheduler()

        thread = threading.Thread(target=_scheduler_loop, daemon=True)
        thread.start()
        _scheduler_started = True


def _archive_completed_tasks() -> None:
    archived_count = archive_completed_tasks()
    logger.info("scheduler: archived completed tasks count=%s", archived_count)


def _scheduler_loop() -> None:
    logger.info("scheduler loop: started")
    while True:
        schedule.run_pending()
        time.sleep(1)
