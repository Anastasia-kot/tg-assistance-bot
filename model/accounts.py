from __future__ import annotations

from config import business_connection_id
from model.ig_stories import has_ig_session, ig_account_label
from model.max_stories import has_max_session
from model.vk_stories import has_vk_session, vk_account_label
from model.wa_stories import has_wa_session, wa_state

STATUS_CONNECTED = "подключён"
STATUS_MISSING = "не подключён"


def accounts_status(telegram_id: int) -> str:
    lines = [
        f"Telegram: {_telegram_status()}",
        f"MAX: {_max_status(telegram_id)}",
        f"WhatsApp: {_whatsapp_status(telegram_id)}",
        f"VK: {_vk_status(telegram_id)}",
        f"Instagram: {_instagram_status(telegram_id)}",
    ]
    return "\n".join(lines)


def _telegram_status() -> str:
    if business_connection_id() is None:
        return f"{STATUS_MISSING} — нет BUSINESS_CONNECTION_ID"
    return f"{STATUS_CONNECTED} — Business API"


def _max_status(telegram_id: int) -> str:
    if has_max_session(telegram_id):
        return f"{STATUS_CONNECTED}"
    return f"{STATUS_MISSING} — /max_login"


def _whatsapp_status(telegram_id: int) -> str:
    if not has_wa_session(telegram_id):
        return f"{STATUS_MISSING} — /wa_login"
    state = wa_state(telegram_id)
    if state == "authorized":
        return f"{STATUS_CONNECTED} — Green-API authorized"
    if state == "notAuthorized":
        return "инстанс сохранён, QR в Green-API не подтверждён"
    if state is None:
        return f"{STATUS_MISSING} — /wa_login"
    return f"инстанс: {state}"


def _vk_status(telegram_id: int) -> str:
    if not has_vk_session(telegram_id):
        return f"{STATUS_MISSING} — /vk_login"
    label = vk_account_label(telegram_id)
    return f"{STATUS_CONNECTED}" + (f" — {label}" if label else "")


def _instagram_status(telegram_id: int) -> str:
    if not has_ig_session(telegram_id):
        return f"{STATUS_MISSING} — /ig_login"
    label = ig_account_label(telegram_id)
    return f"{STATUS_CONNECTED}" + (f" — {label}" if label else "")
