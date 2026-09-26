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


def vk_kate_app_id() -> str:
    return _optional_env("VK_KATE_APP_ID") or "2685278"


def _https_base(raw: str) -> str:
    base = raw.rstrip("/")
    if base.startswith("http://") or base.startswith("https://"):
        return base
    return f"https://{base}"


def vk_public_base_configured() -> bool:
    return bool(
        _optional_env("VK_PUBLIC_BASE")
        or _optional_env("DOMAIN")
        or _optional_env("VK_REDIRECT_URI")
    )


def vk_public_base() -> str:
    custom = _optional_env("VK_PUBLIC_BASE")
    if custom:
        return _https_base(custom)
    # Bothost injects DOMAIN when web interface / domain is enabled.
    domain = _optional_env("DOMAIN")
    if domain:
        return _https_base(domain)
    logger.warning(
        "VK_PUBLIC_BASE and DOMAIN are unset; falling back to DEFAULT_VK_PUBLIC_BASE=%s",
        DEFAULT_VK_PUBLIC_BASE,
    )
    return DEFAULT_VK_PUBLIC_BASE.rstrip("/")


def vk_redirect_uri() -> str:
    custom = _optional_env("VK_REDIRECT_URI")
    if custom:
        return custom
    return f"{vk_public_base()}/vk/callback"
