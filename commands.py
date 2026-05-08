from telebot import types

def register_command_handlers(bot):
    @bot.message_handler(commands=["start"])
    def start_message(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = [
            types.KeyboardButton("Добавить задачу"),
            types.KeyboardButton("Удалить задачу"),
            types.KeyboardButton("Список задач"),
        ]
        markup.add(*buttons)

        bot.send_message(
            message.chat.id,
            text="Привет, {0.first_name} \n👇 Воспользуйся кнопками".format(
                message.from_user
            ),
            reply_markup=markup,
        )

