import telebot

from buttons import register_button_handlers
from commands import register_command_handlers
from compliments import compliments

bot = telebot.TeleBot()

register_command_handlers(bot)
register_button_handlers(bot, compliments)

bot.polling(none_stop=True, interval=0)