import logging
import sys

import telebot

from config import bot_token, business_connection_id, load_env_files
from controller import register_handlers
from version import VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("main")

load_env_files()

token = bot_token()
if not token or ":" not in token:
    logger.error("BOT_TOKEN is missing or invalid.")
    sys.exit(1)

if business_connection_id() is None:
    logger.error("Story publishing is unavailable until BUSINESS_CONNECTION_ID is configured.")

bot = telebot.TeleBot(token)

register_handlers(bot)

logger.info("starting bot polling version: %s", VERSION)
bot.polling(none_stop=True, interval=0)
