import logging

from .init import get_connection
from .schema import ensure_tasks_table

logger = logging.getLogger("database")


def insert_task(task_text: str) -> int:
    normalized_text = (task_text or "").strip()
    if not normalized_text:
        raise ValueError("Task text is empty.")

    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (text) VALUES (%s) RETURNING id;",
                (normalized_text,),
            )
            (task_id,) = cur.fetchone()
            conn.commit()
            logger.info("task added: %s", task_id)
            return int(task_id)


def select_tasks(limit: int = 50):
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, text FROM tasks ORDER BY id DESC LIMIT %s;",
                (limit,),
            )
            return cur.fetchall()

