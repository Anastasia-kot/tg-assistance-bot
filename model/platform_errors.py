from __future__ import annotations


class PlatformStoriesError(Exception):
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class PlatformSessionRequired(PlatformStoriesError):
    def __init__(self, command: str):
        super().__init__(f"Сначала подключите аккаунт: {command}")
        self.command = command
