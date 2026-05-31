import logging
import telebot
import os
from dotenv import load_dotenv

from controller import (
    debug,
    raw_command_handlers,
    register_button_handlers,
    register_callback_handlers,
    register_command_handlers,
)
from model import run_db_check
from model.scheduler import start_scheduler
from version import VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("main")

load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

# подключение к базе данных
run_db_check()

start_scheduler(bot)

raw_command_handlers(bot)
debug.register_handlers(bot)
register_command_handlers(bot)
register_button_handlers(bot)
register_callback_handlers(bot)

logger.info(f"starting bot polling version: {VERSION}")
bot.polling(none_stop=True, interval=0)