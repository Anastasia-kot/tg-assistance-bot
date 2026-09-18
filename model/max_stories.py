from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Coroutine, TypeVar

from maxion.raw import MaxClient
from maxion.raw.device import Device
from maxion.raw.errors import (
    MaxError,
    RpcError,
    SessionExpiredError as MaxionSessionExpiredError,
    TwoFactorRequired,
)
from maxion.raw.opcodes import Opcode
from maxion.raw.session import Session
from maxion.raw.utils import next_cid
from pymax import Client, ExtraConfig, QrAuthFlow
from pymax.session.store import InMemoryStore

logger = logging.getLogger("max_stories")

_T = TypeVar("_T")


class MaxStoriesError(Exception):
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class MaxPasswordRequired(MaxStoriesError):
    def __init__(self, track_id: str):
        super().__init__("Для аккаунта MAX включена двухфакторная защита.")
        self.track_id = track_id


class MaxSessionRequired(MaxStoriesError):
    def __init__(self):
        super().__init__("Сначала подключите аккаунт MAX: /max_login")


class MaxCaptionUnsupported(MaxStoriesError):
    def __init__(self):
        super().__init__(
            "Неофициальный API MAX пока не подтверждает формат текстового слоя. "
            "Удалите текст или выберите публикацию только в Telegram."
        )


def _session_root() -> Path:
    configured = os.getenv("MAX_SESSION_DIR", ".sessions/max")
    return Path(configured).expanduser()


def max_session_path(telegram_id: int) -> Path:
    return _session_root() / f"{int(telegram_id)}.session"


def has_max_session(telegram_id: int) -> bool:
    path = max_session_path(telegram_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False
    return bool(payload.get("token") and payload.get("device_id"))


def _run(factory: Callable[[], Coroutine[Any, Any, _T]]) -> _T:
    return asyncio.run(factory())


class MaxWebSessionUnsupported(MaxStoriesError):
    def __init__(self):
        super().__init__(
            "Текущая MAX-сессия привязана к web-устройству и не публикует истории. "
            "Выйдите через /max_logout и войдите снова по QR — в списке устройств "
            "должна появиться Android-сессия."
        )


def _read_session(telegram_id: int) -> dict[str, Any]:
    path = max_session_path(telegram_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _session_extra(telegram_id: int) -> dict[str, Any]:
    extra = _read_session(telegram_id).get("extra") or {}
    return extra if isinstance(extra, dict) else {}


def is_web_qr_session(telegram_id: int) -> bool:
    extra = _session_extra(telegram_id)
    return extra.get("auth_method") == "qr" and extra.get("device_type") != "ANDROID"


def _device_from_session(telegram_id: int) -> Device:
    user_agent = _session_extra(telegram_id).get("user_agent") or {}
    if not isinstance(user_agent, dict) or not user_agent:
        return Device.android()
    os_version = str(user_agent.get("osVersion") or user_agent.get("os_version") or "Android 13")
    android_version = os_version.removeprefix("Android ").strip() or "13"
    return Device.android(
        device_name=str(
            user_agent.get("deviceName") or user_agent.get("device_name") or "Xiaomi Redmi Note 12"
        ),
        android_version=android_version,
        app_version=str(user_agent.get("appVersion") or user_agent.get("app_version") or "26.29.1"),
        build_number=int(user_agent.get("buildNumber") or user_agent.get("build_number") or 6808),
        arch=str(user_agent.get("arch") or "arm64-v8a"),
        screen=str(
            user_agent.get("screen") or "xxhdpi 480dpi 1080x2400"
        ),
    )


def _max_client(telegram_id: int) -> MaxClient:
    # STORIES_SEND есть только в mobile-протоколе. QR тоже запрашиваем как Android.
    return MaxClient.mobile(
        max_session_path(telegram_id),
        device=_device_from_session(telegram_id),
    )


def _rpc_details(error: BaseException) -> str:
    code = getattr(error, "code", None)
    message = getattr(error, "message", None) or str(error)
    return f"{message} (код {code})" if code is not None else str(message)


def _map_error(error: BaseException, action: str) -> MaxStoriesError:
    if isinstance(error, MaxStoriesError):
        return error
    if isinstance(error, MaxionSessionExpiredError):
        return MaxSessionRequired()
    if isinstance(error, RpcError):
        details = _rpc_details(error)
        opcode_unknown = "неизвестный opcode" in details.lower()
        if opcode_unknown:
            return MaxStoriesError(
                "MAX отклонил публикацию: web-протокол не знает метод историй. "
                "Переподключите MAX через /max_login — бот использует mobile API."
            )
        return MaxStoriesError(f"MAX отклонил операцию «{action}»: {details}")
    if isinstance(error, MaxError):
        return MaxStoriesError(f"Ошибка MAX при операции «{action}»: {error}")
    return MaxStoriesError(f"Не удалось выполнить операцию MAX «{action}».")


def request_max_login_code(telegram_id: int, phone: str) -> str:
    async def _inner() -> str:
        client = _max_client(telegram_id)
        try:
            await client.connect()
            response = await client.request_code(phone)
            token = response.get("token")
            if not token:
                raise MaxStoriesError("MAX не вернул токен подтверждения кода.")
            logger.info(
                "MAX SMS code requested: telegram_id=%s, code_length=%s, "
                "retry_after=%s, requests_left=%s",
                telegram_id,
                response.get("codeLength"),
                response.get("requestMaxDuration"),
                response.get("requestCountLeft"),
            )
            client.session.save()
            return str(token)
        finally:
            await client.disconnect()

    try:
        return _run(_inner)
    except Exception as error:
        logger.exception("MAX code request failed: telegram_id=%s", telegram_id)
        raise _map_error(error, "запрос кода") from error


def login_max_by_qr(
    telegram_id: int,
    show_qr: Callable[[str], None],
) -> str:
    class TelegramQrHandler:
        async def show_qr(self, qr_url: str) -> None:
            await asyncio.to_thread(show_qr, qr_url)

    class UnsupportedPasswordProvider:
        async def get_password(self, hint: str | None = None) -> str:
            raise MaxStoriesError(
                "MAX запросил пароль 2FA после QR. Выберите вход по SMS, "
                "чтобы передать пароль через защищённый шаг диалога."
            )

    async def _inner() -> str:
        store = InMemoryStore()
        auth_flow = QrAuthFlow(
            TelegramQrHandler(),
            password_provider=UnsupportedPasswordProvider(),
        )
        client = Client(
            phone="",
            extra_config=ExtraConfig(
                store=store,
                persist_session=True,
                reconnect=False,
                relogin=False,
            ),
            auth_flow=auth_flow,
        )
        try:
            await client.connect()
            session_info = await store.load_session()
            if session_info is None or not session_info.token:
                raise MaxStoriesError("MAX не вернул сессию после подтверждения QR.")
            profile = client.me
            name = getattr(profile, "name", None) or "MAX"
            user_agent = None
            if session_info.user_agent is not None:
                user_agent = session_info.user_agent.model_dump(
                    by_alias=True,
                    exclude_none=True,
                )
            Session(
                token=session_info.token,
                device_id=session_info.device_id,
                phone=session_info.phone or None,
                user_id=getattr(profile, "id", None) or getattr(profile, "user_id", None),
                name=name,
                extra={
                    "auth_method": "qr",
                    "device_type": "ANDROID",
                    "user_agent": user_agent,
                },
                path=max_session_path(telegram_id),
            ).save()
            mobile = _max_client(telegram_id)
            try:
                await mobile.connect()
                await mobile.login_by_token()
                mobile_name = getattr(getattr(mobile, "me", None), "name", None)
                if mobile_name:
                    name = mobile_name
            finally:
                await mobile.disconnect()
            return str(name)
        finally:
            await client.close()

    try:
        return _run(_inner)
    except Exception as error:
        logger.exception("MAX QR login failed: telegram_id=%s", telegram_id)
        raise _map_error(error, "вход по QR") from error


def confirm_max_login_code(
    telegram_id: int,
    code: str,
    auth_token: str,
) -> str:
    async def _inner() -> str:
        client = _max_client(telegram_id)
        try:
            await client.connect()
            try:
                profile = await client.sign_in(code, auth_token)
            except TwoFactorRequired as error:
                client.session.save()
                challenge = getattr(error, "challenge", {}) or {}
                track_id = challenge.get("trackId") or auth_token
                raise MaxPasswordRequired(str(track_id)) from error
            return profile.name or "MAX"
        finally:
            await client.disconnect()

    try:
        return _run(_inner)
    except MaxPasswordRequired:
        raise
    except Exception as error:
        logger.exception("MAX code confirmation failed: telegram_id=%s", telegram_id)
        raise _map_error(error, "подтверждение кода") from error


def confirm_max_password(
    telegram_id: int,
    password: str,
    track_id: str,
) -> str:
    async def _inner() -> str:
        client = _max_client(telegram_id)
        try:
            await client.connect()
            profile = await client.login_check_password(password, track_id)
            return profile.name or "MAX"
        finally:
            await client.disconnect()

    try:
        return _run(_inner)
    except Exception as error:
        logger.exception("MAX password confirmation failed: telegram_id=%s", telegram_id)
        raise _map_error(error, "проверка 2FA") from error


def validate_max_session(telegram_id: int) -> bool:
    if not has_max_session(telegram_id):
        return False

    async def _inner() -> bool:
        client = _max_client(telegram_id)
        try:
            await client.connect()
            await client.login_by_token()
            return True
        finally:
            await client.disconnect()

    try:
        return _run(_inner)
    except Exception:
        logger.warning(
            "MAX session validation failed: telegram_id=%s",
            telegram_id,
            exc_info=True,
        )
        return False


def logout_max(telegram_id: int) -> None:
    path = max_session_path(telegram_id)

    async def _inner() -> None:
        client = _max_client(telegram_id)
        try:
            await client.connect()
            await client.login_by_token()
            await client.logout()
        finally:
            await client.disconnect()

    try:
        if has_max_session(telegram_id):
            _run(_inner)
    except Exception:
        logger.warning(
            "MAX remote logout failed; removing local session: telegram_id=%s",
            telegram_id,
            exc_info=True,
        )
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _story_send_payloads(media: dict[str, Any]) -> list[dict[str, Any]]:
    cid = next_cid()
    attach = dict(media)
    return [
        {"stories": [{"cid": cid, "media": [attach]}]},
        {"stories": [{"cid": cid, "attaches": [attach]}]},
        {"cid": cid, "media": attach},
    ]


async def _send_story(client: MaxClient, media: dict[str, Any]) -> dict[str, Any]:
    last_error: BaseException | None = None
    for payload in _story_send_payloads(media):
        logger.info(
            "MAX STORIES_SEND shape=%s",
            {key: type(value).__name__ for key, value in payload.items()},
        )
        try:
            return await client.invoke(Opcode.STORIES_SEND, payload)
        except RpcError as error:
            last_error = error
            if str(error.code).lower() != "proto.payload":
                raise
            logger.warning(
                "MAX STORIES_SEND rejected shape error=%s payload=%s",
                error.code,
                error.payload,
            )
    if last_error is not None:
        raise last_error
    raise MaxStoriesError("MAX не принял ни один формат публикации истории.")


def publish_max_photo(
    telegram_id: int,
    image_bytes: bytes,
    caption: str | None,
) -> dict[str, Any]:
    if not has_max_session(telegram_id):
        raise MaxSessionRequired()
    if is_web_qr_session(telegram_id):
        raise MaxWebSessionUnsupported()
    if caption:
        raise MaxCaptionUnsupported()

    async def _inner() -> dict[str, Any]:
        client = _max_client(telegram_id)
        try:
            await client.connect()
            await client.login_by_token()
            media = await client.upload_photo(image_bytes, filename="story.jpg")
            logger.info("MAX photo uploaded keys=%s", sorted(media.keys()))
            return await _send_story(client, media)
        finally:
            await client.disconnect()

    try:
        result = _run(_inner)
        logger.info("MAX story published: telegram_id=%s", telegram_id)
        return result
    except Exception as error:
        logger.exception("MAX story publish failed: telegram_id=%s", telegram_id)
        raise _map_error(error, "публикация истории") from error
