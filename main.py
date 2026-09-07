import logging
import os

import telebot
from dotenv import load_dotenv

from controller import register_handlers
from model import run_db_check
from version import VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("main")

load_dotenv()
if not os.getenv("API_ID") or not os.getenv("API_HASH"):
    logger.warning("API_ID or API_HASH is not set")
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

run_db_check()
register_handlers(bot)

logger.info("starting bot polling version: %s", VERSION)
bot.polling(none_stop=True, interval=0)
