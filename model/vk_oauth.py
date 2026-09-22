from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from typing import Any
from urllib.parse import urlencode

import requests

from config import vk_app_id, vk_client_secret, vk_redirect_uri
from model.vk_stories import VK_API_VERSION, VK_OAUTH_SCOPE, VkStoriesError

logger = logging.getLogger("vk_oauth")

AUTHORIZE_URL = "https://oauth.vk.com/authorize"
ACCESS_TOKEN_URL = "https://oauth.vk.com/access_token"
STATE_TTL_SECONDS = 600


class VkOAuthError(VkStoriesError):
    pass


def vk_oauth_ready() -> bool:
    return bool(vk_app_id() and vk_client_secret() and vk_redirect_uri())


def encode_oauth_state(telegram_id: int, *, now: int | None = None) -> str:
    issued_at = int(now if now is not None else time.time())
    payload = f"{int(telegram_id)}.{issued_at}"
    digest = hmac.new(_state_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{digest}"


def decode_oauth_state(state: str, *, now: int | None = None) -> int:
    parts = (state or "").split(".")
    if len(parts) != 3:
        raise VkOAuthError("Сессия входа во VK устарела. Нажмите /vk_login ещё раз.")
    telegram_raw, issued_raw, digest = parts
    payload = f"{telegram_raw}.{issued_raw}"
    expected = hmac.new(_state_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, expected):
        raise VkOAuthError("Сессия входа во VK недействительна. Нажмите /vk_login ещё раз.")
    try:
        telegram_id = int(telegram_raw)
        issued_at = int(issued_raw)
    except ValueError as error:
        raise VkOAuthError("Сессия входа во VK повреждена. Нажмите /vk_login ещё раз.") from error
    current = int(now if now is not None else time.time())
    if current - issued_at > STATE_TTL_SECONDS or issued_at > current + 30:
        raise VkOAuthError("Сессия входа во VK истекла. Нажмите /vk_login ещё раз.")
    return telegram_id


def vk_authorize_url(telegram_id: int) -> str:
    app_id = vk_app_id()
    redirect_uri = vk_redirect_uri()
    if not app_id or not redirect_uri:
        raise VkOAuthError("VK-приложение не настроено: задайте VK_APP_ID и VK_PUBLIC_BASE.")
    return AUTHORIZE_URL + "?" + urlencode(
        {
            "client_id": app_id,
            "display": "page",
            "redirect_uri": redirect_uri,
            "scope": VK_OAUTH_SCOPE,
            "response_type": "code",
            "v": VK_API_VERSION,
            "state": encode_oauth_state(telegram_id),
            "revoke": 1,
        }
    )


def exchange_vk_code(code: str) -> dict[str, Any]:
    app_id = vk_app_id()
    secret = vk_client_secret()
    redirect_uri = vk_redirect_uri()
    if not app_id or not secret or not redirect_uri:
        raise VkOAuthError("VK-приложение не настроено: задайте VK_APP_ID и VK_CLIENT_SECRET.")
    try:
        response = requests.get(
            ACCESS_TOKEN_URL,
            params={
                "client_id": app_id,
                "client_secret": secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        logger.exception("VK OAuth token exchange failed")
        raise VkOAuthError("Не удалось обменять код VK на токен.", retryable=True) from error
    except ValueError as error:
        raise VkOAuthError("VK вернул не JSON при обмене кода.") from error
    if payload.get("error"):
        description = payload.get("error_description") or payload.get("error")
        logger.error("VK OAuth error: %s", description)
        raise VkOAuthError(f"VK отклонил авторизацию: {description}")
    token = str(payload.get("access_token") or "").strip()
    if not token:
        raise VkOAuthError("VK не вернул access_token.")
    return {
        "access_token": token,
        "user_id": payload.get("user_id"),
        "expires_in": payload.get("expires_in"),
    }


def _state_secret() -> bytes:
    secret = (
        os.getenv("VK_OAUTH_STATE_SECRET")
        or os.getenv("VK_CLIENT_SECRET")
        or os.getenv("BOT_TOKEN")
        or ""
    ).strip()
    if not secret:
        raise VkOAuthError("Не задан секрет для подписи VK OAuth state.")
    return secret.encode("utf-8")
