from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from typing import Optional

MAX_AUTH_CONSENT = "consent"
MAX_AUTH_METHOD = "method"
MAX_AUTH_QR = "qr"
MAX_AUTH_PHONE = "phone"
MAX_AUTH_CODE = "code"
MAX_AUTH_PASSWORD = "password"


@dataclass(frozen=True)
class MaxAuthState:
    step: str
    phone: Optional[str] = None
    auth_token: Optional[str] = None
    track_id: Optional[str] = None


_lock = threading.Lock()
_states: dict[int, MaxAuthState] = {}


def begin_max_auth(telegram_id: int) -> MaxAuthState:
    state = MaxAuthState(step=MAX_AUTH_CONSENT)
    with _lock:
        _states[int(telegram_id)] = state
    return state


def accept_max_auth_risk(telegram_id: int) -> Optional[MaxAuthState]:
    with _lock:
        state = _states.get(int(telegram_id))
        if state is None or state.step != MAX_AUTH_CONSENT:
            return None
        updated = replace(state, step=MAX_AUTH_METHOD)
        _states[int(telegram_id)] = updated
        return updated


def select_max_sms_auth(telegram_id: int) -> Optional[MaxAuthState]:
    with _lock:
        state = _states.get(int(telegram_id))
        if state is None or state.step != MAX_AUTH_METHOD:
            return None
        updated = replace(state, step=MAX_AUTH_PHONE)
        _states[int(telegram_id)] = updated
        return updated


def select_max_qr_auth(telegram_id: int) -> Optional[MaxAuthState]:
    with _lock:
        state = _states.get(int(telegram_id))
        if state is None or state.step != MAX_AUTH_METHOD:
            return None
        updated = replace(state, step=MAX_AUTH_QR)
        _states[int(telegram_id)] = updated
        return updated


def set_max_code_requested(
    telegram_id: int,
    phone: str,
    auth_token: str,
) -> MaxAuthState:
    state = MaxAuthState(
        step=MAX_AUTH_CODE,
        phone=phone,
        auth_token=auth_token,
    )
    with _lock:
        _states[int(telegram_id)] = state
    return state


def set_max_password_requested(
    telegram_id: int,
    track_id: str,
) -> Optional[MaxAuthState]:
    with _lock:
        state = _states.get(int(telegram_id))
        if state is None or state.step != MAX_AUTH_CODE:
            return None
        updated = replace(
            state,
            step=MAX_AUTH_PASSWORD,
            auth_token=None,
            track_id=track_id,
        )
        _states[int(telegram_id)] = updated
        return updated


def get_max_auth(telegram_id: int) -> Optional[MaxAuthState]:
    with _lock:
        return _states.get(int(telegram_id))


def clear_max_auth(telegram_id: int) -> None:
    with _lock:
        _states.pop(int(telegram_id), None)
