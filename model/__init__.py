from typing import Optional

from .schema import check_connection
from .tasks import (
    complete_tasks_by_ids,
    delete_tasks_by_ids,
    get_task_id_by_display_index,
    insert_task,
    select_today_tasks,
    select_tomorrow_tasks,
)


def run_db_check():
    return check_connection()


def list_today_tasks(limit: int = 50):
    return select_today_tasks(limit=limit)


def list_tasks(limit: int = 50):
    return list_today_tasks(limit=limit)


def list_tomorrow_tasks(limit: int = 50):
    return select_tomorrow_tasks(limit=limit)


def get_id_by_index(index: int):
    return get_task_id_by_display_index(index)


def add_task(task_text: str, execute_at: Optional[str] = None) -> int:
    return insert_task(task_text, execute_at)


def delete_tasks(task_ids: list[int]):
    return delete_tasks_by_ids(task_ids)


def complete_tasks(task_ids: list[int]):
    return complete_tasks_by_ids(task_ids)
