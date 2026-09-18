from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from typing import Optional

WA_INSTANCE = "wa_instance"
WA_TOKEN = "wa_token"
VK_TOKEN = "vk_token"
IG_USERNAME = "ig_username"
IG_PASSWORD = "ig_password"
IG_2FA = "ig_2fa"


@dataclass(frozen=True)
class SocialAuthState:
    platform: str
    step: str
    username: Optional[str] = None
    password: Optional[str] = None
    instance_id: Optional[str] = None


_lock = threading.Lock()
_states: dict[int, SocialAuthState] = {}


def begin_social_auth(telegram_id: int, platform: str, step: str) -> SocialAuthState:
    state = SocialAuthState(platform=platform, step=step)
    with _lock:
        _states[int(telegram_id)] = state
    return state


def get_social_auth(telegram_id: int) -> Optional[SocialAuthState]:
    with _lock:
        return _states.get(int(telegram_id))


def set_social_auth(telegram_id: int, **changes) -> Optional[SocialAuthState]:
    with _lock:
        state = _states.get(int(telegram_id))
        if state is None:
            return None
        updated = replace(state, **changes)
        _states[int(telegram_id)] = updated
        return updated


def clear_social_auth(telegram_id: int) -> None:
    with _lock:
        _states.pop(int(telegram_id), None)
