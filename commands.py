from telebot import types
from auth import is_allowed_user
from testdb import add_task, list_tasks

def register_command_handlers(bot):
    @bot.message_handler(commands=["start"])
    def start_message(message):
        if not is_allowed_user(message):
            bot.send_message(message.chat.id, text="Нет доступа.")
            return

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

    @bot.message_handler(func=lambda message: isinstance(message.text, str) and message.text.startswith("/add"))
    def add_task_message(message):
        if not is_allowed_user(message):
            bot.send_message(message.chat.id, text="Нет доступа.")
            return

        task_text = message.text[len("/add") :].strip()
        if not task_text:
            bot.send_message(message.chat.id, text="Используй: /add <текст задачи>")
            return

        task_id = add_task(task_text)
        bot.send_message(message.chat.id, text=f"Задача добавлена (id={task_id}).")

    @bot.message_handler(func=lambda message: isinstance(message.text, str) and message.text.startswith("/list"))
    def list_tasks_message(message):
        if not is_allowed_user(message):
            bot.send_message(message.chat.id, text="Нет доступа.")
            return

        rows = list_tasks()
        if not rows:
            bot.send_message(message.chat.id, text="Список задач пуст.")
            return

        lines = [f"{task_id}. {text}" for task_id, text in rows]
        bot.send_message(message.chat.id, text="\n".join(lines))

