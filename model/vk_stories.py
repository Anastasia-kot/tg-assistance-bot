from __future__ import annotations

import logging
from typing import Any

import requests

from model.platform_errors import PlatformSessionRequired, PlatformStoriesError
from model.session_files import delete_session, has_session, read_session, write_session

logger = logging.getLogger("vk_stories")

PLATFORM = "vk"
VK_API_VERSION = "5.199"
VK_API_URL = "https://api.vk.ru/method/"
LOGIN_COMMAND = "/vk_login"


class VkStoriesError(PlatformStoriesError):
    pass


class VkSessionRequired(PlatformSessionRequired):
    def __init__(self):
        super().__init__(LOGIN_COMMAND)


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
    upload_url = _call(
        "stories.getPhotoUploadServer",
        token,
        {"add_to_news": 1},
    ).get("upload_url")
    if not upload_url:
        raise VkStoriesError("VK не вернул адрес загрузки истории.")
    uploaded = requests.post(
        upload_url,
        files={"file": ("story.jpg", image_bytes, "image/jpeg")},
        timeout=60,
    )
    uploaded.raise_for_status()
    upload_payload = uploaded.json()
    upload_result = upload_payload.get("upload_result")
    if not upload_result:
        raise VkStoriesError("VK не принял файл истории.")
    return _call("stories.save", token, {"upload_results": upload_result})


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
        message = error.get("error_msg") or "ошибка VK"
        raise VkStoriesError(f"VK отклонил операцию «{method}»: {message}")
    return body.get("response")
