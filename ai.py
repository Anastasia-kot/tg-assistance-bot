from gigachat import GigaChat, Chat 
from gigachat.models import Messages, MessagesRole
import os
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """Ты — секретарь юриста. Ты отвечаешь за ведение списка задач.

При получении сообщения от пользователя ты должен определить тип сообщения:
- /delete — удаление задачи
- /list — просмотр списка задач
- /add — добавление задачи
- /complete — завершение задачи

Для каждого типа сообщения ты должен вывести ответ в формате JSON.

Для добавления задачи выведи поля:
- task: /add
- time: время задачи в международном формате, если  указано время, иначе пустое значение.
- description: суть задачи. Исправь ошибки и опечатки, сформулируй кратко в деловом стиле.

Для удаления задачи выведи поля:
- task: /delete
- ids: список id задач

Для просмотра списка задач выведи поля:
- task: /list
- time: время в международном формате, по умолчанию сегодня

Для завершения задачи выведи поля:
- task: /complete
- ids: список id задач
"""

giga_connection = GigaChat(
    credentials=os.getenv("GIGA_API_KEY"),
    # после окончния разработки поставить значение по умолчанию true
    verify_ssl_certs=False,
)


def get_ai_response(user_message: str) -> str:
    chat = Chat(
        messages=[
            Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT),
            Messages(role=MessagesRole.USER, content=user_message),
        ]
    )
    response = giga_connection.chat(chat)
    return response.choices[0].message.content
