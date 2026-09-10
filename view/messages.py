from __future__ import annotations

from typing import Optional

MSG_START_NEED_AUTH = (
    "Этот бот публикует ваши фото в сторис.\n\n"
    "Один раз пришлите api_id и api_hash с my.telegram.org (раздел API development tools) "
    "одним сообщением, например:\n123456:0123456789abcdef0123456789abcdef"
)
MSG_START_READY = "Аккаунт подключён. Пришлите картинку — я спрошу, публиковать ли её в сторис."
MSG_ASK_KEYS = (
    "Пришлите api_id и api_hash одним сообщением в формате:\n"
    "123456:0123456789abcdef0123456789abcdef"
)
MSG_BAD_KEYS = "Не получилось разобрать ключи. Нужен формат: число:хеш, например 123456:0123abcd…"
MSG_KEYS_SAVED = "Ключи сохранены."
MSG_ASK_PHONE = "Пришлите номер телефона в формате +7… или нажмите кнопку ниже."
MSG_ASK_CODE = "Пришлите код, который пришёл в Telegram."
MSG_ASK_2FA = "Пришлите облачный пароль двухэтапной проверки Telegram."
MSG_CODE_SENT = "Код отправлен в Telegram на {phone}. Пришлите его сюда."
MSG_AUTH_DONE = "Аккаунт подключён. Пришлите картинку для сторис."
MSG_STATUS_READY = "Аккаунт подключён. Можно присылать картинки."
MSG_STATUS_NEED = "Аккаунт ещё не подключён. Нажмите /start или /login."
MSG_LOGOUT = "Сессия удалена. Чтобы публиковать сторис, пришлите api_id и api_hash или /login."
MSG_ASK_PUBLISH = "Опубликовать в сторис Telegram?"
MSG_PUBLISHED = "Сторис опубликована."
MSG_CANCELLED = "Отменено. Пришлите новую картинку, когда будете готовы."
MSG_NO_PENDING = "Нет картинки для публикации. Пришлите фото."
MSG_NEED_AUTH_FOR_PHOTO = "Сначала подключите аккаунт: пришлите api_id и api_hash."
MSG_FINISH_AUTH = "Сначала закончите подключение аккаунта."
MSG_BAD_PHONE = "Не получилось разобрать номер. Пришлите его в формате +79001234567."
MSG_PRIVATE_ONLY = "Бот работает только в личных сообщениях."
MSG_UNKNOWN_COMMAND = "Неизвестная команда. Доступны /start, /login, /status, /logout."


def mask_phone(phone: Optional[str]) -> str:
    if not phone:
        return "сохранённый номер"
    digits = phone[-4:] if len(phone) >= 4 else phone
    return f"***{digits}"
