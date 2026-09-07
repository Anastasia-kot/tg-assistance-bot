from .schema import check_connection, ensure_schema


def run_db_check() -> None:
    check_connection()
    ensure_schema()
