from __future__ import annotations

import logging

from .init import get_connection
from .schema import ensure_tasks_table

logger = logging.getLogger(__name__)


def _select_all_tasks() -> list[tuple[int, str, object, object, bool, object]]:
    logger.info("select_all_tasks")
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, text, created_at, execute_at,
                       COALESCE(completed, FALSE), archived_at
                FROM tasks
                ORDER BY id ASC;
                """,
            )
            rows = cur.fetchall()

    result = [
        (int(r[0]), r[1], r[2], r[3], bool(r[4]), r[5])
        for r in rows
    ]
    logger.info("select_all_tasks: returned %s rows", len(result))
    return result


class Debug:
    @staticmethod
    def list_all_tasks():
        return _select_all_tasks()


debug = Debug()
