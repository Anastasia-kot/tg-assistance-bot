from __future__ import annotations

import logging
import re
from typing import Any, Optional

from model.users import (
    AUTH_NEED_2FA,
    AUTH_NEED_CODE,
    AUTH_NEED_KEYS,
    has_app_keys,
    is_ready,
)
from view import (
    MSG_ASK_2FA,
    MSG_ASK_CODE,
    MSG_ASK_KEYS,
    MSG_ASK_PHONE,
    MSG_FINISH_AUTH,
    MSG_PRIVATE_ONLY,
    MSG_START_NEED_AUTH,
    phone_keyboard,
)

logger = logging.getLogger("controller")

_PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def is_private(message) -> bool:
    chat = getattr(message, "chat", None)
    return getattr(chat, "type", None) == "private"


def reject_if_not_private(bot, message) -> bool:
    if is_private(message):
        return False
    chat_id = getattr(getattr(message, "chat", None), "id", None)
    if chat_id is not None:
        bot.send_message(chat_id, MSG_PRIVATE_ONLY)
    return True


def telegram_id_of(update) -> Optional[int]:
    user = getattr(update, "from_user", None)
    user_id = getattr(user, "id", None)
    return int(user_id) if user_id is not None else None


def try_delete(bot, message) -> None:
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        logger.debug("could not delete message", exc_info=True)


def normalize_phone(raw: str) -> Optional[str]:
    compact = re.sub(r"[\s\-()]", "", (raw or "").strip())
    if compact.startswith("8") and len(compact) == 11 and compact.isdigit():
        compact = "+7" + compact[1:]
    if compact.startswith("7") and len(compact) == 11 and compact.isdigit():
        compact = "+" + compact
    if not compact.startswith("+"):
        compact = "+" + compact
    digits = compact[1:]
    if not digits.isdigit() or not (10 <= len(digits) <= 15):
        return None
    if not _PHONE_RE.match(compact):
        return None
    return compact


def looks_like_phone(text: str) -> bool:
    return normalize_phone(text) is not None


def parse_app_keys(text: str) -> Optional[tuple[int, str]]:
    parts = [p.strip() for p in re.split(r"[\s:,;]+", (text or "").strip()) if p.strip()]
    if len(parts) != 2 or not parts[0].isdigit():
        return None
    api_hash = parts[1]
    if len(api_hash) < 16:
        return None
    return int(parts[0]), api_hash


def remind_auth(bot, chat_id: int, user: dict[str, Any]) -> None:
    if is_ready(user):
        return
    state = user.get("auth_state")
    if state == AUTH_NEED_CODE:
        bot.send_message(chat_id, MSG_ASK_CODE)
        return
    if state == AUTH_NEED_2FA:
        bot.send_message(chat_id, MSG_ASK_2FA)
        return
    if has_app_keys(user) and state != AUTH_NEED_KEYS:
        bot.send_message(chat_id, MSG_ASK_PHONE, reply_markup=phone_keyboard())
        return
    bot.send_message(chat_id, MSG_ASK_KEYS)


def prompt_start_auth(bot, chat_id: int) -> None:
    bot.send_message(chat_id, MSG_START_NEED_AUTH)


def prompt_finish_auth(bot, chat_id: int, user: dict[str, Any]) -> None:
    bot.send_message(chat_id, MSG_FINISH_AUTH)
    remind_auth(bot, chat_id, user)
