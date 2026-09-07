from __future__ import annotations

from typing import Any, Optional

from .init import get_connection

AUTH_NEED_PHONE = "need_phone"
AUTH_NEED_CODE = "need_code"
AUTH_NEED_2FA = "need_2fa"
AUTH_READY = "ready"

_USER_COLUMNS = (
    "telegram_id",
    "phone",
    "session_string",
    "phone_code_hash",
    "auth_state",
    "created_at",
    "updated_at",
)


def _row_to_user(row: tuple) -> dict[str, Any]:
    return dict(zip(_USER_COLUMNS, row))


def get_user(telegram_id: int) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT telegram_id, phone, session_string, phone_code_hash,
                       auth_state, created_at, updated_at
                FROM users
                WHERE telegram_id = %s
                """,
                (telegram_id,),
            )
            row = cur.fetchone()
    return _row_to_user(row) if row else None


def ensure_user(telegram_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (telegram_id, auth_state)
                VALUES (%s, %s)
                ON CONFLICT (telegram_id) DO NOTHING
                """,
                (telegram_id, AUTH_NEED_PHONE),
            )
        conn.commit()
    user = get_user(telegram_id)
    assert user is not None
    return user


def is_ready(user: Optional[dict[str, Any]]) -> bool:
    return bool(
        user
        and user.get("auth_state") == AUTH_READY
        and user.get("session_string")
    )


def update_user(
    telegram_id: int,
    *,
    phone: Optional[str] = None,
    session_string: Optional[str] = None,
    phone_code_hash: Optional[str] = None,
    auth_state: Optional[str] = None,
    clear_session: bool = False,
    clear_phone_code_hash: bool = False,
) -> dict[str, Any]:
    assignments = ["updated_at = now()"]
    params: list[Any] = []

    if phone is not None:
        assignments.append("phone = %s")
        params.append(phone)
    if session_string is not None:
        assignments.append("session_string = %s")
        params.append(session_string)
    if clear_session:
        assignments.append("session_string = NULL")
    if phone_code_hash is not None:
        assignments.append("phone_code_hash = %s")
        params.append(phone_code_hash)
    if clear_phone_code_hash:
        assignments.append("phone_code_hash = NULL")
    if auth_state is not None:
        assignments.append("auth_state = %s")
        params.append(auth_state)

    params.append(telegram_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE users SET {', '.join(assignments)} WHERE telegram_id = %s",
                params,
            )
        conn.commit()
    user = get_user(telegram_id)
    assert user is not None
    return user


def save_session(telegram_id: int, session_string: str) -> None:
    update_user(telegram_id, session_string=session_string)


def mark_ready(telegram_id: int, session_string: str) -> dict[str, Any]:
    return update_user(
        telegram_id,
        session_string=session_string,
        auth_state=AUTH_READY,
        clear_phone_code_hash=True,
    )


def reset_login(telegram_id: int, *, keep_phone: bool = True) -> dict[str, Any]:
    assignments = [
        "session_string = NULL",
        "phone_code_hash = NULL",
        "auth_state = %s",
        "updated_at = now()",
    ]
    params: list[Any] = [AUTH_NEED_PHONE]
    if not keep_phone:
        assignments.insert(0, "phone = NULL")
    params.append(telegram_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE users SET {', '.join(assignments)} WHERE telegram_id = %s",
                params,
            )
        conn.commit()
    return ensure_user(telegram_id)
