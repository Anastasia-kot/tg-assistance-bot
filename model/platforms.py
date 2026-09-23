from __future__ import annotations

from dataclasses import dataclass

from config import business_connection_id
from model.vk_oauth import vk_oauth_ready
from model.vk_stories import has_vk_session, vk_account_label

PLATFORM_TELEGRAM = "telegram"
PLATFORM_VK = "vk"
PLATFORM_ORDER = (PLATFORM_TELEGRAM, PLATFORM_VK)
PLATFORM_TITLES = {
    PLATFORM_TELEGRAM: "Telegram",
    PLATFORM_VK: "VK",
}


@dataclass(frozen=True)
class PlatformStatus:
    key: str
    title: str
    connected: bool
    detail: str
    login_url: str | None = None


def platform_statuses(telegram_id: int, *, vk_login_url: str | None = None) -> list[PlatformStatus]:
    return [
        _telegram_status(),
        _vk_status(telegram_id, vk_login_url=vk_login_url),
    ]


def connected_platform_keys(telegram_id: int) -> frozenset[str]:
    return frozenset(item.key for item in platform_statuses(telegram_id) if item.connected)


def default_selected(telegram_id: int) -> frozenset[str]:
    return connected_platform_keys(telegram_id)


def _telegram_status() -> PlatformStatus:
    connected = business_connection_id() is not None
    return PlatformStatus(
        key=PLATFORM_TELEGRAM,
        title=PLATFORM_TITLES[PLATFORM_TELEGRAM],
        connected=connected,
        detail="бизнес-аккаунт бота" if connected else "не задан BUSINESS_CONNECTION_ID",
    )


def _vk_status(telegram_id: int, *, vk_login_url: str | None) -> PlatformStatus:
    connected = has_vk_session(telegram_id)
    if connected:
        detail = vk_account_label(telegram_id) or "аккаунт подключён"
    else:
        detail = "не подключено"
    login_url = None
    if vk_oauth_ready():
        login_url = vk_login_url
    return PlatformStatus(
        key=PLATFORM_VK,
        title=PLATFORM_TITLES[PLATFORM_VK],
        connected=connected,
        detail=detail,
        login_url=login_url,
    )
