import logging
import sys
import time

import telebot
from requests.exceptions import ReadTimeout

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
while True:
    try:
        bot.polling(
            none_stop=True,
            interval=0,
            timeout=20,
            long_polling_timeout=20,
            allowed_updates=[
                "message",
                "callback_query",
                "business_connection",
                "business_message",
            ],
        )
    except ReadTimeout:
        logger.warning("Telegram long poll timed out, retrying")
        time.sleep(2)
