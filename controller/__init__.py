from .callbacks import register_callback_handlers
from .max_login import register_max_login_handlers
from .photos import register_photo_handlers
from .social_login import register_social_login_handlers
from .start import register_start_handlers


def register_handlers(bot) -> None:
    register_max_login_handlers(bot)
    register_social_login_handlers(bot)
    register_start_handlers(bot)
    register_photo_handlers(bot)
    register_callback_handlers(bot)
