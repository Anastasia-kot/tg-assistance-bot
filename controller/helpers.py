from __future__ import annotations

import logging
import re
from typing import Optional

from view import MSG_PRIVATE_ONLY

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
