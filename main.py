import telebot
import os
from dotenv import load_dotenv

from buttons import register_button_handlers
from commands import register_command_handlers
from testdb import run_db_check

load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

run_db_check()

register_command_handlers(bot)
register_button_handlers(bot)

bot.polling(none_stop=True, interval=0)