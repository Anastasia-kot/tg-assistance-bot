from auth import require_allowed_user
from model import debug as model_debug
from view import debug as view_debug


def _register_all_tasks_handler(bot) -> None:
    @bot.message_handler(commands=["_all"])
    @require_allowed_user(bot)
    def all_tasks_message(message):
        view_debug.print_all_tasks(bot, message, model_debug.list_all_tasks())


class Debug:
    @staticmethod
    def register_handlers(bot) -> None:
        _register_all_tasks_handler(bot)


debug = Debug()
