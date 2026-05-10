from __future__ import annotations

from typing import Optional

from .init import get_connection
from .schema import ensure_tasks_table


def insert_task(task_text: str, execute_at: Optional[str] = None) -> int:
    normalized_text = (task_text or "").strip()
    if not normalized_text:
        raise ValueError("Task text is empty.")

    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (text, execute_at) VALUES (%s, %s) RETURNING id;",
                (normalized_text, execute_at),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row[0])


def delete_tasks_by_ids(task_ids: list[int]) -> None:
    if not task_ids:
        return
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = ANY(%s);", (task_ids,))
        conn.commit()


def complete_tasks_by_ids(task_ids: list[int]) -> None:
    if not task_ids:
        return
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET completed = TRUE WHERE id = ANY(%s);",
                (task_ids,),
            )
        conn.commit()


def _sort_key_tasks_display_order(row) -> tuple[int, object]:
    _task_id, _text, is_completed, created_at = row
    completed_first_rank = 0 if is_completed else 1
    return (completed_first_rank, created_at)


def select_tasks(limit: int = 50) -> list[tuple[int, str]]:
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, text, COALESCE(completed, FALSE), created_at
                FROM tasks
                ORDER BY id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = list(cur.fetchall())

    rows.sort(key=_sort_key_tasks_display_order)
    return [(int(r[0]), r[1]) for r in rows]


def get_task_id_by_display_index(display_index: int, limit: int = 50) -> int:
    rows = select_tasks(limit=limit)
    if display_index < 1 or display_index > len(rows):
        raise ValueError("Нет задачи с таким номером.")
    return rows[display_index - 1][0]
