import logging
import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv

logger = logging.getLogger("database")

load_dotenv()


@contextmanager
def get_connection():
    pg_host = os.getenv("PGHOST")
    pg_database = os.getenv("PGDATABASE")
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_port_raw = os.getenv("PGPORT")

    cfg = {
        "host": pg_host,
        "dbname": pg_database,
        "user": pg_user,
        "password": pg_password,
        "port": int(pg_port_raw),
    }

    logger.info("opening db connection: %s", {**cfg, "password": "***"})
    conn = psycopg.connect(**cfg)
    try:
        yield conn
    finally:
        conn.close()

