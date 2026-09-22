from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from typing import Any
from urllib.parse import urlencode

import requests

from config import vk_app_id, vk_client_secret, vk_redirect_uri
from model.vk_stories import VkStoriesError

logger = logging.getLogger("vk_oauth")

AUTHORIZE_URL = "https://id.vk.ru/authorize"
ACCESS_TOKEN_URL = "https://id.vk.ru/oauth2/auth"
STATE_TTL_SECONDS = 600
VK_ID_SCOPE = "vkid.personal_info"

_pkce_lock = threading.Lock()
_pkce_verifiers: dict[str, str] = {}


class VkOAuthError(VkStoriesError):
    pass


def vk_oauth_ready() -> bool:
    return bool(vk_app_id() and vk_client_secret() and vk_redirect_uri())


def encode_oauth_state(telegram_id: int, *, now: int | None = None) -> str:
    issued_at = int(now if now is not None else time.time())
    payload = f"{int(telegram_id)}-{issued_at}"
    digest = hmac.new(_state_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}-{digest}"


def decode_oauth_state(state: str, *, now: int | None = None) -> int:
    parts = (state or "").split("-")
    if len(parts) != 3:
        raise VkOAuthError("Сессия входа во VK устарела. Нажмите /vk_login ещё раз.")
    telegram_raw, issued_raw, digest = parts
    payload = f"{telegram_raw}-{issued_raw}"
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
    state = encode_oauth_state(telegram_id)
    verifier, challenge = _pkce_pair()
    with _pkce_lock:
        _pkce_verifiers[state] = verifier
    return AUTHORIZE_URL + "?" + urlencode(
        {
            "response_type": "code",
            "client_id": app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": VK_ID_SCOPE,
        }
    )


def exchange_vk_code(
    code: str,
    *,
    device_id: str,
    state: str,
) -> dict[str, Any]:
    app_id = vk_app_id()
    secret = vk_client_secret()
    redirect_uri = vk_redirect_uri()
    if not app_id or not secret or not redirect_uri:
        raise VkOAuthError("VK-приложение не настроено: задайте VK_APP_ID и VK_CLIENT_SECRET.")
    if not device_id:
        raise VkOAuthError("VK не вернул device_id. Нажмите /vk_login ещё раз.")
    with _pkce_lock:
        verifier = _pkce_verifiers.pop(state, None)
    if not verifier:
        raise VkOAuthError("Сессия PKCE не найдена. Нажмите /vk_login ещё раз.")
    try:
        response = requests.post(
            ACCESS_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "client_id": app_id,
                "device_id": device_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "service_token": secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        logger.exception("VK ID token exchange failed")
        raise VkOAuthError("Не удалось обменять код VK на токен.", retryable=True) from error
    except ValueError as error:
        raise VkOAuthError("VK вернул не JSON при обмене кода.") from error
    if payload.get("error"):
        description = payload.get("error_description") or payload.get("error")
        logger.error("VK ID OAuth error: %s", description)
        raise VkOAuthError(f"VK отклонил авторизацию: {description}")
    token = str(payload.get("access_token") or "").strip()
    if not token:
        raise VkOAuthError("VK не вернул access_token.")
    return {
        "access_token": token,
        "user_id": payload.get("user_id"),
        "expires_in": payload.get("expires_in"),
        "refresh_token": payload.get("refresh_token"),
        "device_id": device_id,
    }


def parse_vk_callback(query: dict[str, list[str]]) -> dict[str, str]:
    payload_raw = _first(query, "payload")
    if payload_raw:
        try:
            payload = json.loads(payload_raw)
        except ValueError as error:
            raise VkOAuthError("VK вернул битый payload.") from error
        if not isinstance(payload, dict):
            raise VkOAuthError("VK вернул неожиданный payload.")
        return {
            "code": str(payload.get("code") or "").strip(),
            "state": str(payload.get("state") or "").strip(),
            "device_id": str(payload.get("device_id") or "").strip(),
            "error": str(payload.get("error") or "").strip(),
            "error_description": str(payload.get("error_description") or "").strip(),
        }
    return {
        "code": _first(query, "code"),
        "state": _first(query, "state"),
        "device_id": _first(query, "device_id"),
        "error": _first(query, "error"),
        "error_description": _first(query, "error_description"),
    }


def _first(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return (values[0] if values else "").strip()


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64).replace("=", "")
    if len(verifier) < 43:
        verifier = (verifier + "A" * 43)[:64]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


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
