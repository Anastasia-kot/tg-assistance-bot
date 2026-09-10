from __future__ import annotations

import asyncio
import io
import logging
import random
import threading
from contextlib import contextmanager
from typing import Callable, Optional

from telethon import TelegramClient, functions, types
from telethon.errors import (
    AuthKeyUnregisteredError,
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberBannedError,
    PhoneNumberFloodError,
    PhoneNumberInvalidError,
    RPCError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

logger = logging.getLogger("stories")

STORY_PERIOD_SECONDS = 86400

_locks_guard = threading.Lock()
_user_locks: dict[int, threading.Lock] = {}


class StoriesError(Exception):
    """Ошибка, текст которой можно показать пользователю."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class SessionExpiredError(StoriesError):
    def __init__(self):
        super().__init__("Сессия Telegram истекла. Подключите аккаунт ещё раз: /login")


def _lock_for(telegram_id: int) -> threading.Lock:
    with _locks_guard:
        lock = _user_locks.get(telegram_id)
        if lock is None:
            lock = threading.Lock()
            _user_locks[telegram_id] = lock
        return lock


@contextmanager
def user_lock(telegram_id: int):
    lock = _lock_for(telegram_id)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


def _map_rpc(exc: BaseException) -> StoriesError:
    if isinstance(exc, StoriesError):
        return exc
    if isinstance(exc, FloodWaitError):
        return StoriesError(f"Слишком много попыток. Подождите {exc.seconds} сек.")
    if isinstance(exc, PhoneNumberInvalidError):
        return StoriesError("Неверный номер телефона. Пришлите номер в формате +7…")
    if isinstance(exc, PhoneNumberBannedError):
        return StoriesError("Этот номер заблокирован в Telegram.")
    if isinstance(exc, PhoneNumberFloodError):
        return StoriesError("Слишком много запросов кода на этот номер. Подождите и попробуйте снова.")
    if isinstance(exc, PhoneCodeInvalidError):
        return StoriesError("Неверный код. Пришлите код ещё раз.")
    if isinstance(exc, PhoneCodeExpiredError):
        return StoriesError("Код устарел. Нажмите /login и запросите новый.")
    if isinstance(exc, AuthKeyUnregisteredError):
        return SessionExpiredError()
    if isinstance(exc, PasswordHashInvalidError):
        return StoriesError("Неверный облачный пароль. Попробуйте ещё раз.")
    if isinstance(exc, RPCError):
        name = exc.__class__.__name__.upper()
        logger.warning("telegram rpc error: %s", exc.__class__.__name__)
        if "PREMIUM" in name:
            return StoriesError("Telegram не разрешил сторис для этого аккаунта.")
        if "FLOOD" in name or "TOO_MUCH" in name or "TOO MUCH" in name:
            return StoriesError("Слишком часто публикуете сторис. Попробуйте позже.")
        return StoriesError("Telegram отклонил запрос. Попробуйте позже.")
    logger.exception("unexpected telethon error")
    return StoriesError("Не удалось обратиться к Telegram. Попробуйте позже.")


def _run(factory: Callable):
    return asyncio.run(factory())


async def _connect(api_id: int, api_hash: str, session_string: Optional[str]) -> TelegramClient:
    client = TelegramClient(StringSession(session_string or ""), int(api_id), str(api_hash))
    await client.connect()
    return client


def request_login_code(
    api_id: int,
    api_hash: str,
    phone: str,
    session_string: Optional[str] = None,
) -> tuple[str, str]:
    """Отправляет код входа. Возвращает (session_string, phone_code_hash)."""

    async def _inner():
        client = await _connect(api_id, api_hash, session_string)
        try:
            sent = await client.send_code_request(phone)
            return client.session.save(), sent.phone_code_hash
        except Exception as exc:
            raise _map_rpc(exc) from exc
        finally:
            await client.disconnect()

    return _run(_inner)


def sign_in_code(
    api_id: int,
    api_hash: str,
    session_string: str,
    phone: str,
    code: str,
    phone_code_hash: str,
) -> tuple[str, bool]:
    """Вход по коду. Возвращает (session_string, needs_2fa)."""

    async def _inner():
        client = await _connect(api_id, api_hash, session_string)
        try:
            try:
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            except SessionPasswordNeededError:
                return client.session.save(), True
            return client.session.save(), False
        except Exception as exc:
            try:
                saved = client.session.save()
            except Exception:
                saved = session_string
            mapped = _map_rpc(exc)
            if isinstance(mapped, StoriesError) and not isinstance(mapped, SessionExpiredError):
                setattr(mapped, "session_string", saved)
            raise mapped from exc
        finally:
            await client.disconnect()

    return _run(_inner)


def sign_in_password(api_id: int, api_hash: str, session_string: str, password: str) -> str:
    async def _inner():
        client = await _connect(api_id, api_hash, session_string)
        try:
            await client.sign_in(password=password)
            return client.session.save()
        except Exception as exc:
            raise _map_rpc(exc) from exc
        finally:
            await client.disconnect()

    return _run(_inner)


def publish_photo(api_id: int, api_hash: str, session_string: str, image_bytes: bytes) -> str:
    """Публикует фото в сторис. Возвращает обновлённый session_string."""

    async def _inner():
        client = await _connect(api_id, api_hash, session_string)
        saved = session_string
        try:
            if not await client.is_user_authorized():
                raise SessionExpiredError()
            uploaded = await client.upload_file(
                io.BytesIO(image_bytes),
                file_name="story.jpg",
            )
            await client(
                functions.stories.SendStoryRequest(
                    peer=types.InputPeerSelf(),
                    media=types.InputMediaUploadedPhoto(file=uploaded),
                    privacy_rules=[types.InputPrivacyValueAllowAll()],
                    random_id=random.randrange(1, 2**63),
                    period=STORY_PERIOD_SECONDS,
                )
            )
            saved = client.session.save()
            return saved
        except Exception as exc:
            try:
                saved = client.session.save()
            except Exception:
                pass
            mapped = _map_rpc(exc)
            setattr(mapped, "session_string", saved)
            raise mapped from exc
        finally:
            await client.disconnect()

    return _run(_inner)
