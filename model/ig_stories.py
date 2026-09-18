from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from model.platform_errors import PlatformSessionRequired, PlatformStoriesError
from model.session_files import delete_session, session_path

logger = logging.getLogger("ig_stories")

PLATFORM = "instagram"
LOGIN_COMMAND = "/ig_login"


class IgStoriesError(PlatformStoriesError):
    pass


class IgSessionRequired(PlatformSessionRequired):
    def __init__(self):
        super().__init__(LOGIN_COMMAND)


class IgTwoFactorRequired(IgStoriesError):
    def __init__(self, username: str, password: str):
        super().__init__("Instagram запросил код двухфакторной защиты.")
        self.username = username
        self.password = password


def ig_session_file(telegram_id: int) -> Path:
    return session_path(PLATFORM, telegram_id)


def has_ig_session(telegram_id: int) -> bool:
    return ig_session_file(telegram_id).is_file()


def logout_ig(telegram_id: int) -> None:
    delete_session(PLATFORM, telegram_id)


def _instagram():
    from instagrapi import Client
    from instagrapi.exceptions import (
        BadPassword,
        ChallengeRequired,
        LoginRequired,
        TwoFactorRequired,
    )

    return Client, BadPassword, ChallengeRequired, LoginRequired, TwoFactorRequired


def ig_account_label(telegram_id: int) -> str | None:
    path = ig_session_file(telegram_id)
    if not path.is_file():
        return None
    try:
        Client, *_ = _instagram()
        client = Client()
        client.load_settings(path)
        username = getattr(client, "username", None)
        return f"@{username}" if username else "Instagram"
    except Exception:
        return "Instagram"


def validate_ig_session(telegram_id: int) -> bool:
    if not has_ig_session(telegram_id):
        return False
    try:
        client = _client(telegram_id)
        client.get_timeline_feed()
        return True
    except Exception:
        logger.warning(
            "Instagram session validation failed: telegram_id=%s",
            telegram_id,
            exc_info=True,
        )
        return False


def login_instagram(telegram_id: int, username: str, password: str, code: str | None = None) -> str:
    Client, BadPassword, ChallengeRequired, LoginRequired, TwoFactorRequired = _instagram()
    client = Client()
    path = ig_session_file(telegram_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if code:
            client.login(username, password, verification_code=code)
        else:
            client.login(username, password)
    except TwoFactorRequired as error:
        raise IgTwoFactorRequired(username, password) from error
    except BadPassword as error:
        raise IgStoriesError("Неверный пароль Instagram.") from error
    except ChallengeRequired as error:
        raise IgStoriesError(
            "Instagram запросил дополнительное подтверждение в приложении. "
            "Пройдите проверку и повторите /ig_login."
        ) from error
    except LoginRequired as error:
        raise IgStoriesError("Instagram отклонил вход. Проверьте логин и пароль.") from error
    except IgStoriesError:
        raise
    except Exception as error:
        logger.exception("Instagram login failed: telegram_id=%s", telegram_id)
        raise IgStoriesError("Не удалось войти в Instagram.") from error
    client.dump_settings(path)
    os.chmod(path, 0o600)
    return client.username or username


def publish_ig_photo(
    telegram_id: int,
    image_bytes: bytes,
    caption: str | None,
) -> Any:
    if not has_ig_session(telegram_id):
        raise IgSessionRequired()
    _Client, _BadPassword, _ChallengeRequired, LoginRequired, _TwoFactorRequired = _instagram()
    client = _client(telegram_id)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(image_bytes)
            temp_path = Path(temp_file.name)
        return client.photo_upload_to_story(
            temp_path,
            caption=caption or "",
            resize_mode="fit",
        )
    except LoginRequired as error:
        raise IgSessionRequired() from error
    except Exception as error:
        logger.exception("Instagram story publish failed: telegram_id=%s", telegram_id)
        raise IgStoriesError("Не удалось опубликовать историю Instagram.") from error
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def _client(telegram_id: int):
    Client, _BadPassword, _ChallengeRequired, LoginRequired, _TwoFactorRequired = _instagram()
    path = ig_session_file(telegram_id)
    if not path.is_file():
        raise IgSessionRequired()
    client = Client()
    client.load_settings(path)
    try:
        client.get_timeline_feed()
    except LoginRequired:
        client.relogin()
        client.dump_settings(path)
    return client
