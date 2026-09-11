from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

_TOKEN_NAMES = (
    "BOT_TOKEN",
    "API_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_TOKEN",
    "TG_TOKEN",
    "TG_BOT_TOKEN",
    "TOKEN",
)
_TOKEN_SHAPE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{20,}$")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().strip("'").strip('"').strip()
    return text or None


def load_env_files() -> None:
    load_dotenv()
    load_dotenv(Path("/app/.env"))


def first_env(*names: str) -> str | None:
    for name in names:
        value = _clean(os.getenv(name))
        if value:
            return value
    return None


def bot_token() -> str | None:
    for name in _TOKEN_NAMES:
        value = _clean(os.getenv(name))
        if value and _TOKEN_SHAPE.match(value):
            return value
        if value and ":" in value:
            return value
    for key, raw in os.environ.items():
        if "TOKEN" not in key.upper():
            continue
        value = _clean(raw)
        if value and _TOKEN_SHAPE.match(value):
            return value
    return None


def token_env_key_names() -> list[str]:
    return sorted(key for key in os.environ if "TOKEN" in key.upper() or key.upper().endswith("_BOT"))
