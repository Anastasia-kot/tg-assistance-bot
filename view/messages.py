from __future__ import annotations

from typing import Optional

from model.platforms import PlatformStatus

MSG_START_NEED_AUTH = (
    "Этот бот публикует ваши фото в сторис.\n\n"
    "Один раз пришлите api_id и api_hash с my.telegram.org (раздел API development tools) "
    "одним сообщением, например:\n123456:0123456789abcdef0123456789abcdef"
)
MSG_START_READY = (
    "Бот публикует фото в сторис выбранных соцсетей.\n"
    "Подключите аккаунты кнопками ниже, затем пришлите фотографию."
)
MSG_STATUS_READY = "Текущие подключения:"
MSG_ACCOUNTS_HEADER = "Соцсети"
MSG_ASK_PUBLISH = "Отметьте соцсети и нажмите «Опубликовать»."
MSG_PUBLISH_NEED_TARGET = "Выберите хотя бы одну подключённую соцсеть."
MSG_PLATFORM_LOCKED = "Сначала подключите {title}: /start"
MSG_TG_LOGIN_HINT = (
    "Telegram уже публикует сторис в бизнес-аккаунт бота. "
    "Отдельный вход пользователя не нужен."
)
MSG_TG_LOGOUT_HINT = (
    "Telegram нельзя отключить в чате: сторис идут в бизнес-аккаунт бота."
)
MSG_VK_LOGIN_HINT = "VK ещё не настроен. Задайте VK_APP_ID и VK_CLIENT_SECRET."
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
MSG_STATUS_NEED = "Аккаунт ещё не подключён. Нажмите /start или /login."
MSG_LOGOUT = "Сессия удалена. Чтобы публиковать сторис, пришлите api_id и api_hash или /login."
MSG_ASK_CAPTION = "Пришлите текст для сторис одним сообщением."
MSG_CAPTION_TOO_LONG = "Текст слишком длинный. Допустимо не более {limit} символов."
MSG_PUBLISHED = "Сториз опубликована:\n{platforms}"
MSG_VK_ASK_OAUTH = (
    "Нажмите кнопку ниже, разрешите доступ приложению VK "
    "и дождитесь сообщения здесь. Токен в чат копировать не нужно."
)
MSG_VK_OAUTH_NOT_CONFIGURED = (
    "VK-приложение не настроено. Задайте VK_APP_ID и VK_CLIENT_SECRET в окружении."
)
MSG_VK_OAUTH_CALLBACK_OK = (
    "<!doctype html><meta charset='utf-8'><title>VK</title>"
    "<p>VK подключён. Это окно можно закрыть и вернуться в Telegram.</p>"
)
MSG_VK_OAUTH_CALLBACK_FAIL = (
    "<!doctype html><meta charset='utf-8'><title>VK</title>"
    "<p>Не удалось подключить VK.</p><p>{error}</p>"
    "<p>Вернитесь в бота и нажмите /vk_login ещё раз.</p>"
)
MSG_VK_AUTH_DONE = "VK-аккаунт подключён: {name}."
MSG_VK_LOGOUT = "VK-подключение удалено."
MSG_VK_STATUS_READY = "VK-аккаунт подключён: {name}."
MSG_VK_STATUS_NEED = "VK-аккаунт не подключён. Используйте /vk_login."
MSG_VK_STORY_NEEDS_LOGIN = (
    "Для публикации во VK сначала подключите аккаунт: /vk_login. "
    "Подготовленная сторис сохранена."
)
MSG_VK_RETRY_SCHEDULED = (
    "Публикация во VK не удалась. Токен сохранён, повтор через {minutes} мин "
    "(попытка {attempt} из {max_attempts}). Можно отменить.\n\n"
    "{error}"
)
MSG_VK_RETRY_CANCELLED = "Автоповтор публикации во VK отменён."
MSG_VK_TOKEN_OK = "VK-токен живой: stories.getPhotoUploadServer вернул upload_url."
MSG_CANCELLED = "Отменено. Пришлите новую картинку, когда будете готовы."
MSG_NO_PENDING = "Нет картинки для публикации. Пришлите фото."
MSG_NEED_AUTH_FOR_PHOTO = "Сначала подключите аккаунт: пришлите api_id и api_hash."
MSG_FINISH_AUTH = "Сначала закончите подключение аккаунта."
MSG_BUSINESS_CONNECTION_MISSING = (
    "Ошибка конфигурации: BUSINESS_CONNECTION_ID отсутствует или пуст. "
    "Добавьте идентификатор в .env и перезапустите бота."
)
MSG_BAD_PHONE = "Не получилось разобрать номер. Пришлите его в формате +79001234567."
MSG_PRIVATE_ONLY = "Бот работает только в личных сообщениях."
MSG_UNKNOWN_COMMAND = (
    "Неизвестная команда. Доступны /start, /login, /status, /logout, "
    "/vk_login, /vk_status, /vk_logout."
)


def accounts_message(intro: str, statuses: list[PlatformStatus]) -> str:
    lines = [intro, "", MSG_ACCOUNTS_HEADER]
    for status in statuses:
        mark = "✅" if status.connected else "❌"
        lines.append(f"{mark} {status.title}: {status.detail}")
    return "\n".join(lines)


def mask_phone(phone: Optional[str]) -> str:
    if not phone:
        return "сохранённый номер"
    digits = phone[-4:] if len(phone) >= 4 else phone
    return f"***{digits}"
