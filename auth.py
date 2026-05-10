ALLOWED_TG_USERS = {"AnastasiaN11", "ka_borisov"}
ALLOWED_TG_USER_IDS: set[int] = set()


def is_allowed_user(message):
    user = getattr(message, "from_user", None)
    if user is None:
        return False
    username = getattr(user, "username", None)
    user_id = getattr(user, "id", None)
    return (username in ALLOWED_TG_USERS) or (user_id in ALLOWED_TG_USER_IDS)
