import logging
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

logger = logging.getLogger("testdb")

load_dotenv()

logger.info("file loaded")

def run_db_check():
    logger.info("starting db check")
    try:
        import psycopg
    except ModuleNotFoundError as e:
        logger.warning("psycopg is not installed: %s", e)
        return False

    pg_host = os.getenv("PGHOST")
    pg_database = os.getenv("PGDATABASE")
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_port_raw = os.getenv("PGPORT")

    if not (pg_host and pg_database and pg_user and pg_password and pg_port_raw):
        logger.warning(
            "Check that PG* env vars are set. Currently: "
            "PGHOST=%s, PGUSER=%s, PGDATABASE=%s, PGPORT=%s",
            pg_host,
            pg_user,
            pg_database,
            pg_port_raw,
        )
        return False

    try:
        pg_port = int(pg_port_raw)
    except ValueError:
        logger.warning("Invalid PGPORT: %r", pg_port_raw)
        return False

    try:
        with psycopg.connect(
            host=pg_host,
            dbname=pg_database,
            user=pg_user,
            password=pg_password,
            port=pg_port,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_user, current_database(), version();")
                user, db, version = cur.fetchone()
                logger.info("Connected as: %s", user)
                logger.info("Database:     %s", db)
                logger.info("Version:      %s", version)
                return True
    except psycopg.OperationalError as e:
        logger.error("Connection failed: %s", e)
        return False


if __name__ == "__main__":
    run_db_check()