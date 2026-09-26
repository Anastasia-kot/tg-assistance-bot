from __future__ import annotations

from dataclasses import dataclass

from config import business_connection_id
from model.vk_stories import has_vk_session, vk_account_label, vk_auth_method

PLATFORM_TELEGRAM = "telegram"
PLATFORM_VK = "vk"
PLATFORM_ORDER = (PLATFORM_TELEGRAM, PLATFORM_VK)
PLATFORM_TITLES = {
    PLATFORM_TELEGRAM: "Telegram",
    PLATFORM_VK: "VK",
}
AUTH_METHOD_LABELS = {
    "kate": "Kate Mobile",
    "own_app": "VK ID",
}


@dataclass(frozen=True)
class PlatformStatus:
    key: str
    title: str
    connected: bool
    detail: str
    login_url: str | None = None


def platform_statuses(telegram_id: int, *, vk_login_url: str | None = None) -> list[PlatformStatus]:
    del vk_login_url  # method picker replaces direct OAuth URL on the grid
    return [
        _telegram_status(),
        _vk_status(telegram_id),
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


def _vk_status(telegram_id: int) -> PlatformStatus:
    connected = has_vk_session(telegram_id)
    if connected:
        name = vk_account_label(telegram_id) or "аккаунт подключён"
        method = AUTH_METHOD_LABELS.get(vk_auth_method(telegram_id) or "", "")
        detail = f"{name} · {method}" if method else name
    else:
        detail = "не подключено — выберите способ входа"
    return PlatformStatus(
        key=PLATFORM_VK,
        title=PLATFORM_TITLES[PLATFORM_VK],
        connected=connected,
        detail=detail,
        login_url=None,
    )
