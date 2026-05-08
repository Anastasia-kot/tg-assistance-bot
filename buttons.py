import random
from compliments import compliments

def register_button_handlers(bot):
    @bot.message_handler(content_types=["text"])
    def buttons(message):
        if message.text == "Добавить задачу":
            bot.send_message(message.chat.id, text="Ок. Напиши задачу текстом следующим сообщением.")
            return

        if message.text == "Удалить задачу":
            bot.send_message(message.chat.id, text="Ок. Напиши номер/название задачи для удаления.")
            return

        if message.text == "Список задач":
            bot.send_message(message.chat.id, text="Список задач пока пуст.")
            return

        bot.send_message(message.chat.id, text="Я могу отвечать только на нажатие кнопок")

