from gigachat import GigaChat
from gigachat.models import Messages, MessagesRole
import os
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "Ты - секретарь юриста. Ты отвечаешь за ведение списка задач."
    "При получении сообщения от пользователя ты должен определить тип сообщения:
    "'/delete' - удаление задачи"
    "'/list' - просматривание списка задач"
    "'/add' - добавление задачи"
    "'/complete' - завершение задачи"

    "Для каждого типа сообщения ты должен вывести ответ в формате json."
    
    "Для добавления задачи ты должен вывести ответ с полями"
    "'task'='/add', 'time' = время задачи в международном формате, 'description' = суть задачи."
 
    "Для удаления задачи ты должен вывести ответ с полями"
    "'task'='/delete', 'ids' = список id задач."

    "Для просматривания списка задач ты должен вывести ответ с полями"
    "'task'='/list', 'time'= время в международном формате, по умолчанию сегодня"
    
    "Для завершения задачи ты должен вывести ответ с полями"
    "'task'='/complete', 'ids' = список id задач."
)

giga_connection = GigaChat(
    credentials=os.getenv("GIGA_API_KEY"),
    # после окончния разработки поставить значение по умолчанию true
    verify_ssl_certs=False,
)


def chat(user_message: str) -> str:
    messages = [
        Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT),
        Messages(role=MessagesRole.USER, content=user_message),
    ]
    response = giga_connection.chat(messages)
    return response.choices[0].message.content
