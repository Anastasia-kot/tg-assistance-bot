from __future__ import annotations

import logging

from .init import get_connection

logger = logging.getLogger("database")


def check_connection() -> bool:
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


def ensure_schema() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    phone TEXT,
                    session_string TEXT,
                    phone_code_hash TEXT,
                    auth_state TEXT NOT NULL DEFAULT 'need_phone',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_stories (
                    telegram_id BIGINT PRIMARY KEY
                        REFERENCES users(telegram_id) ON DELETE CASCADE,
                    file_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
        conn.commit()
        logger.info("schema ensured")
