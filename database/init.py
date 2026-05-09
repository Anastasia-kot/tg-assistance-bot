import logging
import os

import psycopg
from dotenv import load_dotenv

logger = logging.getLogger("database")

load_dotenv()


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
    return psycopg.connect(**cfg)

