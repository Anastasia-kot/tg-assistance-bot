import logging
import telebot
import os
from dotenv import load_dotenv

from buttons import register_button_handlers
from commands import register_command_handlers
from testdb import run_db_check

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("main")
logger.info("file loaded")

load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

run_db_check()

register_command_handlers(bot)
register_button_handlers(bot)

logger.info("starting bot polling")
bot.polling(none_stop=True, interval=0)