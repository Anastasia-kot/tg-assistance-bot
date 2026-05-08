import os
from dotenv import load_dotenv

load_dotenv()

print("[testdb] file loaded")

def run_db_check():
    print("[testdb] starting db check")
    try:
        import psycopg
    except ModuleNotFoundError as e:
        print(f"psycopg is not installed: {e}")
        return False

    pg_host = os.getenv("PGHOST")
    pg_database = os.getenv("PGDATABASE")
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_port_raw = os.getenv("PGPORT")

    if not (pg_host and pg_database and pg_user and pg_password and pg_port_raw):
        print(
            "Check that PG* env vars are set. Currently: "
            f"PGHOST={pg_host}, PGUSER={pg_user}, PGDATABASE={pg_database}, PGPORT={pg_port_raw}"
        )
        return False

    try:
        pg_port = int(pg_port_raw)
    except ValueError:
        print(f"Invalid PGPORT: {pg_port_raw!r}")
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
                print(f"Connected as: {user}")
                print(f"Database:     {db}")
                print(f"Version:      {version}")
                return True
    except psycopg.OperationalError as e:
        print(f"Connection failed: {e}")
        return False