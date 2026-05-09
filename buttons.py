from auth import is_allowed_user
from database import list_tasks

def register_button_handlers(bot):
    @bot.message_handler(content_types=["text"])
    def buttons(message):
        if message.text == "Добавить задачу":
            if not is_allowed_user(message):
                bot.send_message(message.chat.id, text="Нет доступа.")
                return
            bot.send_message(message.chat.id, text="Ок. Напиши задачу текстом следующим сообщением.")
            return

        if message.text == "Удалить задачу":
            if not is_allowed_user(message):
                bot.send_message(message.chat.id, text="Нет доступа.")
                return
            bot.send_message(message.chat.id, text="Ок. Напиши номер/название задачи для удаления.")
            return

        if message.text == "Список задач":
            if not is_allowed_user(message):
                bot.send_message(message.chat.id, text="Нет доступа.")
                return
            rows = list_tasks()
            if not rows:
                bot.send_message(message.chat.id, text="Список задач пуст.")
                return

            lines = [f"{task_id}. {text}" for task_id, text in rows]
            bot.send_message(message.chat.id, text="\n".join(lines))
            return

        bot.send_message(message.chat.id, text="Я могу отвечать только на нажатие кнопок")

