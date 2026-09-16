from __future__ import annotations

import threading
from typing import Any, Optional

AUTH_NEED_KEYS = "need_keys"
AUTH_NEED_PHONE = "need_phone"
AUTH_NEED_CODE = "need_code"
AUTH_NEED_2FA = "need_2fa"
AUTH_READY = "ready"

_lock = threading.Lock()
_users: dict[int, dict[str, Any]] = {}


def _blank(telegram_id: int) -> dict[str, Any]:
    return {
        "telegram_id": telegram_id,
        "api_id": None,
        "api_hash": None,
        "phone": None,
        "session_string": None,
        "phone_code_hash": None,
        "auth_state": AUTH_NEED_KEYS,
    }


def get_user(telegram_id: int) -> Optional[dict[str, Any]]:
    with _lock:
        user = _users.get(int(telegram_id))
        return dict(user) if user else None


def ensure_user(telegram_id: int) -> dict[str, Any]:
    telegram_id = int(telegram_id)
    with _lock:
        if telegram_id not in _users:
            _users[telegram_id] = _blank(telegram_id)
        return dict(_users[telegram_id])


def has_app_keys(user: Optional[dict[str, Any]]) -> bool:
    return bool(user and user.get("api_id") and user.get("api_hash"))


def app_credentials(user: dict[str, Any]) -> tuple[int, str]:
    return int(user["api_id"]), str(user["api_hash"])


def is_ready(user: Optional[dict[str, Any]]) -> bool:
    return bool(
        user
        and user.get("auth_state") == AUTH_READY
        and user.get("session_string")
        and has_app_keys(user)
    )


def update_user(
    telegram_id: int,
    *,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
    phone: Optional[str] = None,
    session_string: Optional[str] = None,
    phone_code_hash: Optional[str] = None,
    auth_state: Optional[str] = None,
    clear_session: bool = False,
    clear_phone_code_hash: bool = False,
    clear_keys: bool = False,
    clear_phone: bool = False,
) -> dict[str, Any]:
    telegram_id = int(telegram_id)
    with _lock:
        user = _users.setdefault(telegram_id, _blank(telegram_id))
        if api_id is not None:
            user["api_id"] = api_id
        if api_hash is not None:
            user["api_hash"] = api_hash
        if clear_keys:
            user["api_id"] = None
            user["api_hash"] = None
        if phone is not None:
            user["phone"] = phone
        if clear_phone:
            user["phone"] = None
        if session_string is not None:
            user["session_string"] = session_string
        if clear_session:
            user["session_string"] = None
        if phone_code_hash is not None:
            user["phone_code_hash"] = phone_code_hash
        if clear_phone_code_hash:
            user["phone_code_hash"] = None
        if auth_state is not None:
            user["auth_state"] = auth_state
        return dict(user)


def save_session(telegram_id: int, session_string: str) -> None:
    update_user(telegram_id, session_string=session_string)


def mark_ready(telegram_id: int, session_string: str) -> dict[str, Any]:
    return update_user(
        telegram_id,
        session_string=session_string,
        auth_state=AUTH_READY,
        clear_phone_code_hash=True,
    )


def reset_login(
    telegram_id: int,
    *,
    keep_phone: bool = True,
    keep_keys: bool = True,
) -> dict[str, Any]:
    user = ensure_user(telegram_id)
    keep_existing_keys = keep_keys and has_app_keys(user)
    next_state = AUTH_NEED_PHONE if keep_existing_keys else AUTH_NEED_KEYS
    return update_user(
        telegram_id,
        auth_state=next_state,
        clear_session=True,
        clear_phone_code_hash=True,
        clear_keys=not keep_existing_keys,
        clear_phone=not keep_phone,
    )
