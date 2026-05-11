ALLOWED_TG_USERS = {"AnastasiaN11", "ka_borisov"}
ALLOWED_TG_USER_IDS = {1601552168}


def _chat_id_from_update(update) -> int | None:
    chat = getattr(update, "chat", None)
    if chat is not None:
        chat_id = getattr(chat, "id", None)
        if chat_id is not None:
            return int(chat_id)
    inner = getattr(update, "message", None)
    if inner is not None:
        chat = getattr(inner, "chat", None)
        if chat is not None:
            chat_id = getattr(chat, "id", None)
            if chat_id is not None:
                return int(chat_id)
    return None


def is_allowed_user(message):
    user = getattr(message, "from_user", None)
    if user is None:
        return False
    username = getattr(user, "username", None)
    user_id = getattr(user, "id", None)
    return (username in ALLOWED_TG_USERS) or (user_id in ALLOWED_TG_USER_IDS)


def require_allowed_user(bot):
    def decorator(handler):
        def wrapped(message):
            chat_id = _chat_id_from_update(message)
            if not is_allowed_user(message):
                if chat_id is not None:
                    bot.send_message(chat_id, text="Нет доступа.")
                return
            if chat_id is not None:
                from model.notifications import set_notification_chat_id

                set_notification_chat_id(chat_id)
            return handler(message)

        return wrapped

    return decorator
