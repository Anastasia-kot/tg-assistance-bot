from __future__ import annotations

import logging
from typing import Any

import requests

from model.platform_errors import PlatformSessionRequired, PlatformStoriesError
from model.session_files import delete_session, has_session, read_session, write_session

logger = logging.getLogger("wa_stories")

PLATFORM = "whatsapp"
LOGIN_COMMAND = "/wa_login"


class WaStoriesError(PlatformStoriesError):
    pass


class WaSessionRequired(PlatformSessionRequired):
    def __init__(self):
        super().__init__(LOGIN_COMMAND)


def _hosts(id_instance: str) -> tuple[str, str]:
    cluster = str(id_instance)[:4]
    return (
        f"https://{cluster}.api.green-api.com",
        f"https://{cluster}.media.green-api.com",
    )


def save_wa_credentials(
    telegram_id: int,
    id_instance: str,
    api_token: str,
) -> str:
    api_url, media_url = _hosts(id_instance)
    state = _get_state(api_url, id_instance, api_token)
    write_session(
        PLATFORM,
        telegram_id,
        {
            "id_instance": id_instance,
            "api_token": api_token,
            "api_url": api_url,
            "media_url": media_url,
            "state": state,
        },
    )
    return state


def has_wa_session(telegram_id: int) -> bool:
    return has_session(PLATFORM, telegram_id, "id_instance", "api_token")


def logout_wa(telegram_id: int) -> None:
    delete_session(PLATFORM, telegram_id)


def validate_wa_session(telegram_id: int) -> bool:
    return wa_state(telegram_id) == "authorized"


def wa_state(telegram_id: int) -> str | None:
    if not has_wa_session(telegram_id):
        return None
    creds = read_session(PLATFORM, telegram_id)
    try:
        return _get_state(
            str(creds["api_url"]),
            str(creds["id_instance"]),
            str(creds["api_token"]),
        )
    except Exception:
        logger.warning(
            "WhatsApp session validation failed: telegram_id=%s",
            telegram_id,
            exc_info=True,
        )
        return "unknown"


def publish_wa_photo(
    telegram_id: int,
    image_bytes: bytes,
    caption: str | None,
) -> dict[str, Any]:
    if not has_wa_session(telegram_id):
        raise WaSessionRequired()
    creds = read_session(PLATFORM, telegram_id)
    state = _get_state(
        str(creds["api_url"]),
        str(creds["id_instance"]),
        str(creds["api_token"]),
    )
    if state != "authorized":
        raise WaStoriesError(
            "WhatsApp-инстанс Green-API не авторизован. "
            "Отсканируйте QR в кабинете Green-API и повторите публикацию."
        )
    upload_url = (
        f"{creds['media_url']}/waInstance{creds['id_instance']}"
        f"/uploadFile/{creds['api_token']}"
    )
    try:
        uploaded = requests.post(
            upload_url,
            files={"file": ("story.jpg", image_bytes, "image/jpeg")},
            timeout=60,
        )
        uploaded.raise_for_status()
        upload_payload = uploaded.json()
    except requests.RequestException as error:
        logger.exception("WhatsApp upload failed: telegram_id=%s", telegram_id)
        raise WaStoriesError("Не удалось загрузить файл в Green-API.") from error
    url_file = upload_payload.get("urlFile")
    if not url_file:
        raise WaStoriesError("Green-API не вернул ссылку на загруженный файл.")
    send_url = (
        f"{creds['api_url']}/waInstance{creds['id_instance']}"
        f"/sendMediaStatus/{creds['api_token']}"
    )
    body: dict[str, Any] = {
        "urlFile": url_file,
        "fileName": "story.jpg",
        "participants": [],
    }
    if caption:
        body["caption"] = caption[:1024]
    try:
        sent = requests.post(send_url, json=body, timeout=60)
        sent.raise_for_status()
        return sent.json()
    except requests.RequestException as error:
        logger.exception("WhatsApp status send failed: telegram_id=%s", telegram_id)
        raise WaStoriesError("Green-API отклонил публикацию статуса WhatsApp.") from error


def _get_state(api_url: str, id_instance: str, api_token: str) -> str:
    url = f"{api_url}/waInstance{id_instance}/getStateInstance/{api_token}"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        raise WaStoriesError(
            "Не удалось проверить инстанс Green-API. Проверьте idInstance и токен."
        ) from error
    state = payload.get("stateInstance")
    if not state:
        raise WaStoriesError("Green-API не вернул состояние инстанса.")
    return str(state)
