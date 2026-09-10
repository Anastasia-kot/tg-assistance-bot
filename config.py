from __future__ import annotations

import os


def first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return None


def bot_token() -> str | None:
    return first_env("BOT_TOKEN", "API_TOKEN", "TELEGRAM_BOT_TOKEN")
