from __future__ import annotations

import io
import logging
import os
from typing import Any
from urllib.parse import urlencode

import requests
from PIL import Image

from model.platform_errors import PlatformSessionRequired, PlatformStoriesError
from model.session_files import delete_session, has_session, read_session, write_session

logger = logging.getLogger("vk_stories")

PLATFORM = "vk"
VK_API_VERSION = "5.199"
VK_API_URL = "https://api.vk.ru/method/"
LOGIN_COMMAND = "/vk_login"
DEFAULT_VK_APP_ID = "2685278"
VK_OAUTH_REDIRECT = "https://oauth.vk.com/blank.html"
VK_OAUTH_SCOPE = "stories,offline"


class VkStoriesError(PlatformStoriesError):
    pass


class VkSessionRequired(PlatformSessionRequired):
    def __init__(self):
        super().__init__(LOGIN_COMMAND)


def vk_oauth_url() -> str:
    app_id = (os.getenv("VK_APP_ID") or DEFAULT_VK_APP_ID).strip() or DEFAULT_VK_APP_ID
    return "https://oauth.vk.com/authorize?" + urlencode(
        {
            "client_id": app_id,
            "display": "page",
            "redirect_uri": VK_OAUTH_REDIRECT,
            "scope": VK_OAUTH_SCOPE,
            "response_type": "token",
            "v": VK_API_VERSION,
            "revoke": 1,
        }
    )


def save_vk_token(telegram_id: int, access_token: str) -> dict[str, Any]:
    profile = _users_get(access_token)
    write_session(
        PLATFORM,
        telegram_id,
        {
            "access_token": access_token,
            "user_id": profile.get("id"),
            "name": _display_name(profile),
        },
    )
    return profile


def has_vk_session(telegram_id: int) -> bool:
    return has_session(PLATFORM, telegram_id, "access_token")


def logout_vk(telegram_id: int) -> None:
    delete_session(PLATFORM, telegram_id)


def validate_vk_session(telegram_id: int) -> bool:
    if not has_vk_session(telegram_id):
        return False
    try:
        _users_get(_token(telegram_id))
        return True
    except Exception:
        logger.warning("VK session validation failed: telegram_id=%s", telegram_id, exc_info=True)
        return False


def vk_account_label(telegram_id: int) -> str | None:
    return read_session(PLATFORM, telegram_id).get("name")


def publish_vk_photo(
    telegram_id: int,
    image_bytes: bytes,
    caption: str | None,
) -> dict[str, Any]:
    if not has_vk_session(telegram_id):
        raise VkSessionRequired()
    token = _token(telegram_id)
    params: dict[str, Any] = {"add_to_news": 1}
    upload_url = _call("stories.getPhotoUploadServer", token, params).get("upload_url")
    if not upload_url:
        raise VkStoriesError("VK не вернул адрес загрузки истории.")
    jpeg = _as_jpeg(image_bytes)
    try:
        uploaded = requests.post(
            upload_url,
            files={"file": ("story.jpg", jpeg, "image/jpeg")},
            timeout=60,
        )
        uploaded.raise_for_status()
        upload_payload = uploaded.json()
    except requests.RequestException as error:
        logger.exception("VK story upload failed")
        raise VkStoriesError("Не удалось загрузить файл истории во VK.") from error
    except ValueError as error:
        raise VkStoriesError("VK вернул не JSON при загрузке истории.") from error
    upload_error = upload_payload.get("error") if isinstance(upload_payload, dict) else None
    if upload_error:
        raise VkStoriesError(f"VK не принял файл истории: {upload_error}")
    upload_result = _extract_upload_result(upload_payload)
    if not upload_result:
        raise VkStoriesError("VK не принял файл истории.")
    return _call("stories.save", token, {"upload_results": upload_result})


def _as_jpeg(image_bytes: bytes) -> bytes:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != "RGB":
            image = image.convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        return buffer.getvalue()
    except Exception:
        logger.debug("could not convert story image to JPEG", exc_info=True)
        return image_bytes


def _extract_upload_result(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    result = payload.get("upload_result")
    if result:
        return str(result)
    response = payload.get("response")
    if isinstance(response, dict) and response.get("upload_result"):
        return str(response["upload_result"])
    return None


def _token(telegram_id: int) -> str:
    token = read_session(PLATFORM, telegram_id).get("access_token")
    if not token:
        raise VkSessionRequired()
    return str(token)


def _users_get(access_token: str) -> dict[str, Any]:
    response = _call("users.get", access_token, {"fields": "screen_name"})
    if not response:
        raise VkStoriesError("VK не вернул профиль. Проверьте токен.")
    return response[0]


def _display_name(profile: dict[str, Any]) -> str:
    first = profile.get("first_name") or ""
    last = profile.get("last_name") or ""
    name = f"{first} {last}".strip()
    screen = profile.get("screen_name")
    if screen:
        return f"{name} (@{screen})" if name else f"@{screen}"
    return name or str(profile.get("id") or "VK")


def _call(method: str, access_token: str, params: dict[str, Any] | None = None) -> Any:
    payload = {"v": VK_API_VERSION, "access_token": access_token}
    if params:
        payload.update(params)
    try:
        response = requests.post(VK_API_URL + method, data=payload, timeout=30)
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as error:
        logger.exception("VK request failed: method=%s", method)
        raise VkStoriesError(f"Не удалось обратиться к VK API ({method}).") from error
    error = body.get("error")
    if error:
        raise VkStoriesError(_vk_error_message(method, error))
    return body.get("response")


def _vk_error_message(method: str, error: dict[str, Any]) -> str:
    code = error.get("error_code")
    message = error.get("error_msg") or "ошибка VK"
    if code == 5:
        return (
            "Токен VK недействителен или отозван. "
            "Выйдите через /vk_logout и подключитесь заново: /vk_login."
        )
    if code == 15:
        return (
            "VK запретил stories для этого токена. "
            "Нужен пользовательский access_token с правом stories."
        )
    return f"VK отклонил операцию «{method}»: {message}"
