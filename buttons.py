import random

def register_button_handlers(bot, compliments):
    @bot.message_handler(content_types=["text"])
    def buttons(message):
        if message.text == "Старт":
            bot.send_message(
                message.chat.id,
                text="Я могу поддержать тебя и поднять настроение. Просто попроси об этом",
            )
            return

        if message.text == "Комплимент":
            bot.send_message(message.chat.id, text=str(random.choice(compliments)))
            return

        bot.send_message(message.chat.id, text="Я могу отвечать только на нажатие кнопок")

