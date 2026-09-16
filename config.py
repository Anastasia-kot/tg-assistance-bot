from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger("config")


def load_env_files() -> None:
    load_dotenv()
    load_dotenv(Path("/app/.env"))


def _env_value(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        logger.error("environment variable %s is missing", name)
        return None
    text = value.strip().strip("'").strip('"').strip()
    if not text:
        logger.error("environment variable %s is empty", name)
        return None
    return text


def bot_token() -> str | None:
    return _env_value("BOT_TOKEN")


def business_connection_id() -> str | None:
    return _env_value("BUSINESS_CONNECTION_ID")
