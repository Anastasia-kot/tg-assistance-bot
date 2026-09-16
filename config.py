from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_env_files() -> None:
    load_dotenv()
    load_dotenv(Path("/app/.env"))


def bot_token() -> str | None:
    value = os.getenv("BOT_TOKEN")
    if value is None:
        return None
    text = value.strip().strip("'").strip('"').strip()
    return text or None
