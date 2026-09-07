from __future__ import annotations

from typing import Optional

from .init import get_connection


def set_pending(telegram_id: int, file_id: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pending_stories (telegram_id, file_id, created_at)
                VALUES (%s, %s, now())
                ON CONFLICT (telegram_id) DO UPDATE
                SET file_id = EXCLUDED.file_id,
                    created_at = now()
                """,
                (telegram_id, file_id),
            )
        conn.commit()


def get_pending(telegram_id: int) -> Optional[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT file_id FROM pending_stories WHERE telegram_id = %s",
                (telegram_id,),
            )
            row = cur.fetchone()
    return row[0] if row else None


def pop_pending(telegram_id: int) -> Optional[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM pending_stories
                WHERE telegram_id = %s
                RETURNING file_id
                """,
                (telegram_id,),
            )
            row = cur.fetchone()
        conn.commit()
    return row[0] if row else None


def clear_pending(telegram_id: int) -> None:
    pop_pending(telegram_id)
