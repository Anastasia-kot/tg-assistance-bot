from .callbacks import register_callback_handlers
from .login import register_login_handlers
from .photos import register_photo_handlers
from .start import register_start_handlers


def register_handlers(bot) -> None:
    register_start_handlers(bot)
    register_photo_handlers(bot)
    register_callback_handlers(bot)
    register_login_handlers(bot)
