from telebot import types

def register_command_handlers(bot):
    @bot.message_handler(commands=["start"])
    def start_message(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        start_button = types.KeyboardButton("Старт")
        action_button = types.KeyboardButton("Комплимент")
        markup.add(start_button, action_button)

        bot.send_message(
            message.chat.id,
            text="Привет, {0.first_name} \n👇 Воспользуйся кнопками".format(
                message.from_user
            ),
            reply_markup=markup,
        )

