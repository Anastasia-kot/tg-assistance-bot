from __future__ import annotations

import logging
from typing import Optional

from .init import get_connection
from .schema import ensure_tasks_table

logger = logging.getLogger(__name__)


def insert_task(task_text: str, execute_at: Optional[str] = None) -> int:
    normalized_text = (task_text or "").strip()
    if not normalized_text:
        raise ValueError("Task text is empty.")

    logger.info(
        "insert_task: inserting task text_len=%s execute_at=%s",
        len(normalized_text),
        execute_at,
    )
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (text, execute_at) VALUES (%s, %s) RETURNING id;",
                (normalized_text, execute_at),
            )
            row = cur.fetchone()
            conn.commit()
            task_id = int(row[0])
            logger.info("insert_task: created task id=%s", task_id)
            return task_id


def delete_tasks_by_ids(task_ids: list[int]) -> None:
    if not task_ids:
        logger.info("delete_tasks_by_ids: skipped (empty id list)")
        return
    logger.info("delete_tasks_by_ids: deleting ids=%s", task_ids)
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = ANY(%s);", (task_ids,))
        conn.commit()
    logger.info("delete_tasks_by_ids: done ids=%s", task_ids)


def complete_tasks_by_ids(task_ids: list[int]) -> None:
    if not task_ids:
        logger.info("complete_tasks_by_ids: skipped (empty id list)")
        return
    logger.info("complete_tasks_by_ids: completing ids=%s", task_ids)
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET completed = TRUE WHERE id = ANY(%s);",
                (task_ids,),
            )
        conn.commit()
    logger.info("complete_tasks_by_ids: done ids=%s", task_ids)


def archive_completed_tasks() -> int:
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET archived_at = now()
                WHERE archived_at IS NULL
                  AND COALESCE(completed, FALSE) = TRUE;
                """,
            )
            archived_count = cur.rowcount
        conn.commit()
    logger.info("archive_completed_tasks: archived %s tasks", archived_count)
    return archived_count


def _sort_key_tasks_display_order(row) -> tuple[int, object]:
    _task_id, _text, is_completed, created_at, _execute_at = row
    completed_first_rank = 0 if is_completed else 1
    return (completed_first_rank, created_at)


def select_today_tasks(limit: int = 50) -> list[tuple[int, str, bool, object]]:
    logger.info("select_today_tasks: limit=%s", limit)
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, text, COALESCE(completed, FALSE), created_at, execute_at
                FROM tasks
                WHERE archived_at IS NULL
                  AND (execute_at IS NULL OR execute_at::date <= now()::date)
                ORDER BY id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = list(cur.fetchall())

    rows.sort(key=_sort_key_tasks_display_order)
    result = [(int(r[0]), r[1], bool(r[2]), r[4]) for r in rows]
    logger.info(
        "select_today_tasks: returned %s rows (limit=%s)",
        len(result),
        limit,
    )
    return result


def select_tomorrow_tasks(limit: int = 50) -> list[tuple[int, str, bool, object]]:
    logger.info("select_tomorrow_tasks: limit=%s", limit)
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, text, COALESCE(completed, FALSE), created_at, execute_at
                FROM tasks
                WHERE archived_at IS NULL
                  AND execute_at::date = (now()::date + INTERVAL '1 day')
                ORDER BY id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = list(cur.fetchall())

    rows.sort(key=_sort_key_tasks_display_order)
    result = [(int(r[0]), r[1], bool(r[2]), r[4]) for r in rows]
    logger.info(
        "select_tomorrow_tasks: returned %s rows (limit=%s)",
        len(result),
        limit,
    )
    return result


def get_task_id_by_display_index(display_index: int, limit: int = 50) -> int:
    logger.info(
        "get_task_id_by_display_index: display_index=%s limit=%s",
        display_index,
        limit,
    )
    rows = select_tasks(limit=limit)
    if display_index < 1 or display_index > len(rows):
        logger.warning(
            "get_task_id_by_display_index: invalid index display_index=%s row_count=%s",
            display_index,
            len(rows),
        )
        raise ValueError("Нет задачи с таким номером.")
    task_id = rows[display_index - 1][0]
    logger.info(
        "get_task_id_by_display_index: display_index=%s -> task_id=%s",
        display_index,
        task_id,
    )
    return task_id
