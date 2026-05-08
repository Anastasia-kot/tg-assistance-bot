ALLOWED_TG_USERNAMES = {"AnastasiaN11", "ka_borisov"}


def is_allowed_user(message):
    username = getattr(getattr(message, "from_user", None), "username", None)
    return username in ALLOWED_TG_USERNAMES

