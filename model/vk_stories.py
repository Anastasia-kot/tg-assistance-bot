from __future__ import annotations

import json
import io
import logging
import os
from typing import Any
from urllib.parse import urlencode

import requests
from PIL import Image

from model.session_files import delete_session, has_session, read_session, write_session

logger = logging.getLogger("vk_stories")

PLATFORM = "vk"
VK_API_VERSION = "5.199"
VK_API_URL = "https://api.vk.ru/method/"
LOGIN_COMMAND = "/vk_login"
DEFAULT_VK_APP_ID = "2685278"
VK_OAUTH_REDIRECT = "https://oauth.vk.com/blank.html"
VK_OAUTH_SCOPE = "stories,offline"
VK_STORIES_PERMISSION = 8_388_608
VK_PERMISSION_BITS = {
    "notify": 1,
    "friends": 2,
    "photos": 4,
    "audio": 8,
    "video": 16,
    "questions": 64,
    "pages": 128,
    "status": 1024,
    "notes": 2048,
    "messages": 4096,
    "wall": 8192,
    "ads": 32768,
    "offline": 65536,
    "docs": 131072,
    "groups": 262144,
    "notifications": 524288,
    "stats": 1048576,
    "email": 4194304,
    "stories": VK_STORIES_PERMISSION,
    "market": 134217728,
}
USER_ERROR_LIMIT = 3500


class VkStoriesError(Exception):
    def __init__(self, user_message: str, *, retryable: bool = False):
        super().__init__(user_message)
        self.user_message = user_message
        self.retryable = retryable


class VkFloodError(VkStoriesError):
    def __init__(self, user_message: str):
        super().__init__(user_message, retryable=True)


class VkSessionRequired(VkStoriesError):
    def __init__(self):
        super().__init__(f"Сначала подключите аккаунт VK: {LOGIN_COMMAND}")


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


def parse_vk_token(raw: str) -> str:
    text = (raw or "").strip()
    if "error=" in text and "access_token=" not in text:
        return ""
    if "access_token=" in text:
        after = text.split("access_token=", 1)[1]
        return after.split("&", 1)[0].strip()
    return text


def save_vk_token(telegram_id: int, access_token: str) -> dict[str, Any]:
    try:
        profile = _users_get(access_token)
    except VkFloodError:
        write_session(
            PLATFORM,
            telegram_id,
            {
                "access_token": access_token,
                "user_id": None,
                "name": "VK",
            },
        )
        logger.warning(
            "VK users.get flooded while saving token: telegram_id=%s, token kept",
            telegram_id,
        )
        raise
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


def check_vk_token(telegram_id: int) -> dict[str, Any]:
    if not has_vk_session(telegram_id):
        return {
            "ok": False,
            "retryable": False,
            "has_upload_url": False,
            "error": f"Сначала подключите аккаунт VK: {LOGIN_COMMAND}",
        }
    token = _token(telegram_id)
    try:
        _log_token_permissions(telegram_id, token)
        upload_url = _call(
            "stories.getPhotoUploadServer",
            token,
            {"add_to_news": 1},
        ).get("upload_url")
    except VkStoriesError as error:
        logger.warning(
            "VK token check failed: telegram_id=%s retryable=%s error=%s",
            telegram_id,
            error.retryable,
            error.user_message,
        )
        return {
            "ok": False,
            "retryable": error.retryable,
            "has_upload_url": False,
            "error": error.user_message,
        }
    if not upload_url:
        return {
            "ok": False,
            "retryable": True,
            "has_upload_url": False,
            "error": "VK не вернул адрес загрузки истории.",
        }
    logger.info("VK token check ok: telegram_id=%s has_upload_url=True", telegram_id)
    return {
        "ok": True,
        "retryable": False,
        "has_upload_url": True,
        "error": None,
    }


def validate_vk_session(telegram_id: int) -> bool:
    return bool(check_vk_token(telegram_id).get("ok"))


def vk_account_label(telegram_id: int) -> str | None:
    return read_session(PLATFORM, telegram_id).get("name")


def publish_vk_photo(
    telegram_id: int,
    image_bytes: bytes,
    caption: str | None = None,
) -> dict[str, Any]:
    del caption
    if not has_vk_session(telegram_id):
        raise VkSessionRequired()
    token = _token(telegram_id)
    _log_token_permissions(telegram_id, token)
    upload_url = _call(
        "stories.getPhotoUploadServer",
        token,
        {"add_to_news": 1},
    ).get("upload_url")
    if not upload_url:
        raise VkStoriesError(
            "VK не вернул адрес загрузки истории.",
            retryable=True,
        )
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
        raise VkStoriesError(
            "Не удалось загрузить файл истории во VK.",
            retryable=True,
        ) from error
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
        raise VkStoriesError(
            f"Не удалось обратиться к VK API ({method}).",
            retryable=True,
        ) from error
    error = body.get("error")
    if error:
        _raise_vk_error(method, error)
    return body.get("response")


def decode_vk_permissions(mask: int) -> list[str]:
    names = [
        name
        for name, bit in sorted(VK_PERMISSION_BITS.items(), key=lambda item: item[1])
        if mask & bit
    ]
    return names


def _log_token_permissions(telegram_id: int, access_token: str) -> None:
    mask = _call("account.getAppPermissions", access_token)
    try:
        mask_int = int(mask)
    except (TypeError, ValueError):
        logger.warning(
            "VK account.getAppPermissions unexpected payload telegram_id=%s payload=%s",
            telegram_id,
            mask,
        )
        return
    scopes = decode_vk_permissions(mask_int)
    has_stories = bool(mask_int & VK_STORIES_PERMISSION)
    logger.info(
        "VK token permissions: telegram_id=%s mask=%s scopes=%s stories_bit=%s",
        telegram_id,
        mask_int,
        scopes,
        has_stories,
    )
    if not has_stories:
        logger.warning(
            "VK getAppPermissions has no stories bit; "
            "Kate/user tokens often omit it. Checking via getPhotoUploadServer. "
            "telegram_id=%s mask=%s scopes=%s",
            telegram_id,
            mask_int,
            scopes,
        )


def _is_flood_error(error: dict[str, Any]) -> bool:
    code = error.get("error_code")
    message = str(error.get("error_msg") or "").lower()
    return code == 9 or "flood" in message


def _raise_vk_error(method: str, error: dict[str, Any]) -> None:
    payload = json.dumps(error, ensure_ascii=False, indent=2)
    if len(payload) > USER_ERROR_LIMIT:
        payload = payload[:USER_ERROR_LIMIT] + "…"
    logger.error("VK API error method=%s payload=%s", method, payload)
    if _is_flood_error(error):
        raise VkFloodError(
            f"VK отклонил операцию «{method}»: flood control "
            f"(код {error.get('error_code')}). "
            "Это лимит запросов, не про права на сторис. "
            "Токен не сбрасывайте — повторите через 10–15 минут.\n\n"
            f"Полный ответ VK:\n{payload}"
        )
    message = error.get("error_msg") or "ошибка VK"
    code = error.get("error_code")
    if code == 5:
        summary = (
            "Токен VK недействителен или отозван. "
            "Выйдите через /vk_logout и подключитесь заново: /vk_login."
        )
    elif code == 15:
        summary = (
            "VK запретил операцию для этого токена "
            f"(«{method}», код 15). Нужно право stories."
        )
    else:
        summary = f"VK отклонил операцию «{method}»: {message}"
    raise VkStoriesError(f"{summary}\n\nПолный ответ VK:\n{payload}")
