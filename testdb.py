import logging
import os
import psycopg
from dotenv import load_dotenv

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

logger = logging.getLogger("testdb")

load_dotenv()

logger.info("file loaded")

def _get_pg_config():
    pg_host = os.getenv("PGHOST")
    pg_database = os.getenv("PGDATABASE")
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_port_raw = os.getenv("PGPORT")

    if not (pg_host and pg_database and pg_user and pg_password and pg_port_raw):
        raise ValueError(
            "Missing PG* env vars. Expected PGHOST, PGDATABASE, PGUSER, PGPASSWORD, PGPORT."
        )

    return {
        "host": pg_host,
        "dbname": pg_database,
        "user": pg_user,
        "password": pg_password,
        "port": int(pg_port_raw),
    }


def get_connection():
    cfg = _get_pg_config()
    logger.info("opening db connection")
    return psycopg.connect(**cfg)


def ensure_tasks_table(conn):
    logger.info("ensuring tasks table")
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id BIGSERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
    conn.commit()


def add_task(task_text: str) -> int:
    normalized_text = (task_text or "").strip()
    if not normalized_text:
        raise ValueError("Task text is empty.")

    logger.info("adding task")
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


def list_tasks(limit: int = 50):
    logger.info("listing tasks")
    with get_connection() as conn:
        ensure_tasks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, text FROM tasks ORDER BY id DESC LIMIT %s;",
                (limit,),
            )
            return cur.fetchall()


def run_db_check():
    logger.info("starting db check")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, current_database(), version();")
            user, db, version = cur.fetchone()
            logger.info("Connected as: %s", user)
            logger.info("Database:     %s", db)
            logger.info("Version:      %s", version)
            return True


if __name__ == "__main__":
    run_db_check()