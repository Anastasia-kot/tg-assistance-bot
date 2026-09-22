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


DEFAULT_VK_PUBLIC_BASE = (
    "https://bot-1778084510-9776-anastasia-kot-ramble.bothost.tech"
)


def bot_token() -> str | None:
    return _env_value("BOT_TOKEN")


def business_connection_id() -> str | None:
    return _env_value("BUSINESS_CONNECTION_ID")


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    text = value.strip().strip("'").strip('"').strip()
    return text or None


def vk_app_id() -> str | None:
    return _optional_env("VK_APP_ID")


def vk_client_secret() -> str | None:
    return _optional_env("VK_CLIENT_SECRET")


def vk_public_base() -> str:
    return (_optional_env("VK_PUBLIC_BASE") or DEFAULT_VK_PUBLIC_BASE).rstrip("/")


def vk_redirect_uri() -> str:
    custom = _optional_env("VK_REDIRECT_URI")
    if custom:
        return custom
    return f"{vk_public_base()}/vk/callback"
