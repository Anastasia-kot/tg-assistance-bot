from typing import Optional

from .schema import check_connection
from .tasks import (
    complete_tasks_by_ids,
    delete_tasks_by_ids,
    get_task_id_by_display_index,
    insert_task,
    select_tasks,
)


def run_db_check():
    return check_connection()


def list_tasks(limit: int = 50):
    return select_tasks(limit=limit)


def get_id_by_index(index: int):
    return get_task_id_by_display_index(index)


def add_task(task_text: str, execute_at: Optional[str] = None) -> int:
    return insert_task(task_text, execute_at)


def delete_tasks(tasks_ids: list[int]):
    return delete_tasks_by_ids(tasks_ids)


def complete_tasks(tasks_ids: list[int]):
    return complete_tasks_by_ids(tasks_ids)
