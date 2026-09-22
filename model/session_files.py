from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


def session_root(platform: str) -> Path:
    configured = os.getenv("SESSION_DIR", ".sessions")
    return Path(configured).expanduser() / platform


def session_path(platform: str, telegram_id: int) -> Path:
    return session_root(platform) / f"{int(telegram_id)}.session"


def read_session(platform: str, telegram_id: int) -> dict[str, Any]:
    path = session_path(platform, telegram_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_session(platform: str, telegram_id: int, payload: dict[str, Any]) -> Path:
    path = session_path(platform, telegram_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def delete_session(platform: str, telegram_id: int) -> None:
    try:
        session_path(platform, telegram_id).unlink()
    except FileNotFoundError:
        pass


def has_session(platform: str, telegram_id: int, *required_keys: str) -> bool:
    payload = read_session(platform, telegram_id)
    if not payload:
        return False
    return all(payload.get(key) for key in required_keys) if required_keys else True
