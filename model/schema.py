import logging

from .init import get_connection

logger = logging.getLogger("database")


def ensure_tasks_table(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id BIGSERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                execute_at TIMESTAMPTZ,
                completed BOOLEAN
            );
            """
        )
        cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS execute_at TIMESTAMPTZ;")
        cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed BOOLEAN DEFAULT FALSE;")
    conn.commit()


def check_connection():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, current_database(), version();")
            user, db, version = cur.fetchone()
            logger.info(
                "Connected as: %s, database: %s, version: %s",
                user,
                db,
                version,
            )
            return True

