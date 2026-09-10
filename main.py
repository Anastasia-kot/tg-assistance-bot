import logging
import sys

import telebot
from dotenv import load_dotenv

from config import bot_token
from controller import register_handlers
from model import run_db_check
from version import VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("main")

load_dotenv()

token = bot_token()
if not token or ":" not in token:
    logger.error(
        "BOT_TOKEN is missing or invalid. Set BOT_TOKEN, API_TOKEN, or TELEGRAM_BOT_TOKEN."
    )
    sys.exit(1)

bot = telebot.TeleBot(token)

run_db_check()
register_handlers(bot)

logger.info("starting bot polling version: %s", VERSION)
bot.polling(none_stop=True, interval=0)
