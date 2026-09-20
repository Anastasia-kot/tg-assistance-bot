from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Coroutine, TypeVar

from maxion.raw import MaxClient
from maxion.raw.device import WEB_HEADER_UA, Device
from maxion.raw.enums import AuthType
from maxion.raw.errors import (
    MaxError,
    NotConnectedError,
    RpcError,
    SessionExpiredError as MaxionSessionExpiredError,
    TimeoutError_ as MaxTimeout,
    TransportError,
    TwoFactorRequired,
)
from maxion.raw.opcodes import Opcode
from maxion.raw.session import Session
from maxion.raw.utils import next_cid
from pymax import ExtraConfig, QrAuthFlow, WebClient
from pymax.exceptions import ApiError as PyMaxApiError
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
            "MAX публикует истории только из Android-приложения. "
            "Сейчас вход через QR (web-сессия) — сториз так не создать. "
            "Выйдите через /max_logout и войдите по SMS."
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
    device_type = str(extra.get("device_type") or "").upper()
    if extra.get("auth_method") == "qr":
        return True
    return device_type == "WEB"


def _web_device_from_session(telegram_id: int) -> Device:
    user_agent = _session_extra(telegram_id).get("user_agent") or {}
    if not isinstance(user_agent, dict):
        user_agent = {}
    return Device.web(
        device_name=str(
            user_agent.get("deviceName") or user_agent.get("device_name") or "Chrome"
        ),
        os_version=str(
            user_agent.get("osVersion") or user_agent.get("os_version") or "Linux"
        ),
        app_version=str(
            user_agent.get("appVersion") or user_agent.get("app_version") or "26.2.2"
        ),
        screen=str(user_agent.get("screen") or "1080x1920 1.0x"),
        locale=str(user_agent.get("locale") or "ru"),
        device_locale=str(
            user_agent.get("deviceLocale") or user_agent.get("device_locale") or "ru"
        ),
        timezone=str(user_agent.get("timezone") or "Europe/Moscow"),
        header_user_agent=str(
            user_agent.get("headerUserAgent")
            or user_agent.get("header_user_agent")
            or WEB_HEADER_UA
        ),
    )


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
    if is_web_qr_session(telegram_id):
        return MaxClient.web(
            max_session_path(telegram_id),
            device=_web_device_from_session(telegram_id),
            auto_reconnect=False,
        )
    return MaxClient.mobile(
        max_session_path(telegram_id),
        device=_device_from_session(telegram_id),
        auto_reconnect=False,
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
    if isinstance(error, PyMaxApiError):
        code = (error.error or "").lower()
        if code == "qr_login.disabled":
            return MaxStoriesError(
                "MAX отключил QR-вход для этого клиента. "
                "Войдите по SMS: /max_login → Войти по SMS."
            )
        details = error.localized_message or error.message or str(error)
        return MaxStoriesError(f"MAX отклонил операцию «{action}»: {details}")
    if isinstance(error, RpcError):
        details = _rpc_details(error)
        lowered = details.lower()
        if "fail_wrong_password" in lowered or "login.cred" in lowered:
            return MaxStoriesError(
                "MAX не принял сохранённую сессию: токен не подходит к устройству. "
                "Выйдите через /max_logout и войдите заново. "
                "Для историй надёжнее SMS-вход."
            )
        if "login.token" in lowered:
            return MaxStoriesError(
                "MAX-сессия истекла. Выйдите через /max_logout и войдите заново "
                "(/max_login → QR или SMS)."
            )
        if "not.ready" in lowered or "not.processed" in lowered:
            return MaxStoriesError(
                "MAX ещё обрабатывает видео истории. Подождите и повторите."
            )
        opcode_unknown = "неизвестный opcode" in lowered
        if opcode_unknown:
            return MaxWebSessionUnsupported()
        return MaxStoriesError(f"MAX отклонил операцию «{action}»: {details}")
    if isinstance(error, TransportError):
        return MaxStoriesError(
            f"MAX оборвал соединение во время операции «{action}». Повторите."
        )
    if isinstance(error, MaxTimeout):
        return MaxStoriesError(
            f"MAX не ответил на операцию «{action}». Повторите."
        )
    if isinstance(error, MaxError):
        return MaxStoriesError(f"Ошибка MAX при операции «{action}»: {error}")
    if isinstance(error, RuntimeError) and "QR authentication expired" in str(error):
        return MaxStoriesError(
            "QR-код истёк до подтверждения. Запустите /max_login и отсканируйте новый код."
        )
    return MaxStoriesError(f"Не удалось выполнить операцию MAX «{action}».")


def request_max_login_code(
    telegram_id: int,
    phone: str,
    *,
    resend: bool = False,
    call: bool = False,
) -> str:
    if call:
        auth_type = AuthType.CALL_RESET
    elif resend:
        auth_type = AuthType.RESEND_CODE
    else:
        auth_type = AuthType.START_AUTH
    # mode=["SMS"] даёт proto.payload («Expected byte array at 42») и рвёт TCP.
    modes: tuple[Any, ...] = (None,)

    async def _inner() -> str:
        client = _max_client(telegram_id)
        last_error: BaseException | None = None
        try:
            await client.connect()
            response = None
            for mode in modes:
                if not getattr(client, "is_connected", False):
                    await client.connect()
                try:
                    response = await client.request_code(
                        phone,
                        auth_type=auth_type,
                        mode=mode,
                    )
                    break
                except RpcError as error:
                    last_error = error
                    if str(error.code).lower() != "proto.payload":
                        raise
                    logger.warning(
                        "MAX AUTH_REQUEST rejected mode=%s error=%s payload=%s",
                        mode,
                        error.code,
                        error.payload,
                    )
                    await client.disconnect()
                except (NotConnectedError, TransportError) as error:
                    last_error = error
                    logger.warning(
                        "MAX AUTH_REQUEST transport failed mode=%s error=%s",
                        mode,
                        error,
                    )
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
            if response is None:
                if last_error is not None:
                    raise last_error
                raise MaxStoriesError("MAX не принял запрос кода.")
            token = response.get("token")
            if not token:
                raise MaxStoriesError("MAX не вернул токен подтверждения кода.")
            logger.info(
                "MAX SMS code requested: telegram_id=%s, type=%s, "
                "code_length=%s, retry_after=%s, requests_left=%s, keys=%s",
                telegram_id,
                auth_type,
                response.get("codeLength"),
                response.get("requestMaxDuration"),
                response.get("requestCountLeft"),
                sorted(response),
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
        client = WebClient(
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
            session_path = max_session_path(telegram_id)
            Session(
                token=session_info.token,
                device_id=session_info.device_id,
                phone=session_info.phone or None,
                user_id=getattr(profile, "id", None) or getattr(profile, "user_id", None),
                name=name,
                extra={
                    "auth_method": "qr",
                    "device_type": "WEB",
                    "user_agent": user_agent,
                },
                path=session_path,
            ).save()
            web = _max_client(telegram_id)
            try:
                await web.connect()
                await web.login_by_token()
                web.session.save()
                web_name = getattr(getattr(web, "me", None), "name", None)
                if web_name:
                    name = web_name
            except Exception as web_error:
                logger.exception(
                    "MAX QR token rejected by web protocol: telegram_id=%s",
                    telegram_id,
                )
                try:
                    session_path.unlink()
                except FileNotFoundError:
                    pass
                raise MaxStoriesError(
                    "QR подтверждён, но MAX не принял web-сессию повторно. "
                    "Войдите по SMS: /max_login → Войти по SMS."
                ) from web_error
            finally:
                await web.disconnect()
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


STORY_SEND_TIMEOUT_SECONDS = 8.0
STORY_TTL_MS = 86_400_000
STORY_VIDEO_SECONDS = 3
ATTACH_RETRY_ATTEMPTS = 6
ATTACH_RETRY_DELAY_SECONDS = 2.0


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
    except ImportError as error:
        raise MaxStoriesError(
            "Для историй MAX нужен пакет imageio-ffmpeg."
        ) from error
    return imageio_ffmpeg.get_ffmpeg_exe()


def _image_to_story_mp4(image_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "story.jpg"
        dst = Path(tmp) / "story.mp4"
        src.write_bytes(image_bytes)
        result = subprocess.run(
            [
                _ffmpeg_exe(),
                "-y",
                "-loop",
                "1",
                "-i",
                str(src),
                "-t",
                str(STORY_VIDEO_SECONDS),
                "-vf",
                "scale=720:1280:force_original_aspect_ratio=decrease,"
                "pad=720:1280:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                "-c:v",
                "libx264",
                "-tune",
                "stillimage",
                "-pix_fmt",
                "yuv420p",
                "-r",
                "30",
                "-movflags",
                "+faststart",
                str(dst),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
            logger.error("ffmpeg story encode failed: %s", result.stderr[-2000:])
            raise MaxStoriesError("Не удалось подготовить видео для истории MAX.")
        logger.info("MAX story video encoded bytes=%s", dst.stat().st_size)
        return dst.read_bytes()


def _story_send_payloads(media: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "stories": [
                {
                    "cid": next_cid(),
                    "media": dict(media),
                    "expiration": STORY_TTL_MS,
                }
            ]
        }
    ]


def _is_retryable_story_error(error: RpcError) -> bool:
    blob = f"{error.code} {error.message}".lower()
    return (
        str(error.code).lower() == "proto.payload"
        or "not.ready" in blob
        or "not.processed" in blob
    )


def _extract_token(blob: Any) -> str | None:
    if isinstance(blob, dict):
        for key in ("token", "videoToken"):
            value = blob.get(key)
            if isinstance(value, str) and value:
                return value
        for value in blob.values():
            found = _extract_token(value)
            if found:
                return found
    if isinstance(blob, list):
        for item in blob:
            found = _extract_token(item)
            if found:
                return found
    return None


async def _request_video_slot(client: MaxClient) -> dict[str, Any]:
    await _ensure_authorized(client)
    info = await client.request_video_upload()
    logger.info(
        "MAX VIDEO_UPLOAD slot_keys=%s",
        sorted((info.get("info") or [{}])[0]) if info.get("info") else sorted(info),
    )
    if not info.get("info"):
        raise MaxStoriesError("MAX не выдал слот для видео истории.")
    return info


async def _upload_story_media(client: MaxClient, image_bytes: bytes) -> dict[str, Any]:
    video_bytes = _image_to_story_mp4(image_bytes)
    info = await _request_video_slot(client)
    slot = (info.get("info") or [])[0]
    video_id = int(slot["videoId"])
    waiter = client._attach_waiter("videoId", video_id)
    posted = await client._post_upload(
        slot["url"], video_bytes, "story.mp4", "video/mp4"
    )
    ready = await client._await_attach(waiter, 120.0)
    logger.info(
        "MAX story video processed attach_keys=%s http_upload=%s",
        sorted(ready) if isinstance(ready, dict) else ready,
        posted if not isinstance(posted, dict) else sorted(posted),
    )
    media: dict[str, Any] = {"_type": "VIDEO", "videoId": video_id}
    token = _extract_token(ready) or _extract_token(posted)
    if token:
        media["token"] = token
    logger.info("MAX story video uploaded keys=%s", sorted(media))
    return media


def _payload_shape(payload: dict[str, Any]) -> dict[str, Any]:
    shape: dict[str, Any] = {key: type(value).__name__ for key, value in payload.items()}
    stories = payload.get("stories")
    if isinstance(stories, list) and stories and isinstance(stories[0], dict):
        shape["storyKeys"] = sorted(stories[0])
        if "expiration" in stories[0]:
            shape["storyExpiration"] = stories[0]["expiration"]
        media = stories[0].get("media")
        if isinstance(media, dict):
            shape["mediaType"] = media.get("_type")
            shape["mediaKeys"] = sorted(media)
    return shape


async def _ensure_authorized(client: MaxClient) -> None:
    if getattr(client, "is_connected", False):
        return
    await client.connect()
    await client.login_by_token()
    client.session.save()


async def _send_story(client: MaxClient, media: dict[str, Any]) -> dict[str, Any]:
    last_error: BaseException | None = None
    for payload in _story_send_payloads(media):
        logger.info("MAX STORIES_SEND shape=%s", _payload_shape(payload))
        for attempt in range(1, ATTACH_RETRY_ATTEMPTS + 1):
            await _ensure_authorized(client)
            try:
                return await client.invoke(
                    Opcode.STORIES_SEND,
                    payload,
                    timeout=STORY_SEND_TIMEOUT_SECONDS,
                )
            except RpcError as error:
                last_error = error
                logger.warning(
                    "MAX STORIES_SEND rejected attempt=%s error=%s payload=%s",
                    attempt,
                    error.code,
                    error.payload,
                )
                if not _is_retryable_story_error(error):
                    raise
                if str(error.code).lower() == "proto.payload":
                    break
                await asyncio.sleep(ATTACH_RETRY_DELAY_SECONDS)
            except (TransportError, MaxTimeout) as error:
                last_error = error
                logger.warning("MAX STORIES_SEND dropped error=%s", error)
                try:
                    await client.disconnect()
                except Exception:
                    logger.debug("MAX disconnect after story send failed", exc_info=True)
                break
    if last_error is not None:
        raise last_error
    raise MaxStoriesError("MAX не принял видео-историю.")


def publish_max_photo(
    telegram_id: int,
    image_bytes: bytes,
    caption: str | None,
) -> dict[str, Any]:
    if not has_max_session(telegram_id):
        raise MaxSessionRequired()
    if caption:
        raise MaxCaptionUnsupported()
    if is_web_qr_session(telegram_id):
        raise MaxWebSessionUnsupported()

    async def _inner() -> dict[str, Any]:
        client = _max_client(telegram_id)
        try:
            await client.connect()
            await client.login_by_token()
            client.session.save()
            media = await _upload_story_media(client, image_bytes)
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
