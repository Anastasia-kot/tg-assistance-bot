import logging
import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv

logger = logging.getLogger("database")

load_dotenv()


@contextmanager
def get_connection():
    cfg = {
        "host": os.getenv("PGHOST"),
        "dbname": os.getenv("PGDATABASE"),
        "user": os.getenv("PGUSER"),
        "password": os.getenv("PGPASSWORD"),
        "port": int(os.getenv("PGPORT")),
    }

    logger.info("opening db connection: %s", {**cfg, "password": "***"})
    conn = psycopg.connect(**cfg)
    try:
        yield conn
    finally:
        conn.close()

