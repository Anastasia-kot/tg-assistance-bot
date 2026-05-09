from .schema import check_connection, ensure_tasks_table
from .tasks import insert_task, select_tasks


def run_db_check():
    return check_connection()


def add_task(task_text: str) -> int:
    return insert_task(task_text)


def list_tasks(limit: int = 50):
    return select_tasks(limit=limit)

