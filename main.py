import logging
import sys

from config import bot_token, business_connection_id, load_env_files, vk_public_base, vk_redirect_uri
from controller import register_handlers
from http_app import serve_http, set_bot, start_polling_thread
from version import VERSION
import telebot

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
set_bot(bot)
try:
    bot.set_my_commands(
        [
            telebot.types.BotCommand("start", "Открыть меню подключений"),
            telebot.types.BotCommand("status", "Статус соцсетей"),
            telebot.types.BotCommand("login", "Подключить Telegram"),
            telebot.types.BotCommand("logout", "Выйти из Telegram"),
            telebot.types.BotCommand("vk_login", "Подключить VK"),
            telebot.types.BotCommand("vk_logout", "Выйти из VK"),
            telebot.types.BotCommand("vk_status", "Статус VK"),
        ]
    )
except Exception:
    logger.exception("failed to set bot commands menu")
logger.info(
    "VK public_base=%s redirect_uri=%s version=%s",
    vk_public_base(),
    vk_redirect_uri(),
    VERSION,
)
logger.info("starting bot polling version: %s", VERSION)
start_polling_thread(bot)
serve_http()
