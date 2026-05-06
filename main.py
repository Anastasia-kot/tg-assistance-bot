import telebot
import os
from dotenv import load_dotenv

from buttons import register_button_handlers
from commands import register_command_handlers

load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

register_command_handlers(bot)
register_button_handlers(bot)

bot.polling(none_stop=True, interval=0)