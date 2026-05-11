ALLOWED_TG_USERS = {"AnastasiaN11", "ka_borisov"}
ALLOWED_TG_USER_IDS={1601552168}


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
            if not is_allowed_user(message):
                bot.send_message(message.chat.id, text="Нет доступа.")
                return
            return handler(message)

        return wrapped

    return decorator
