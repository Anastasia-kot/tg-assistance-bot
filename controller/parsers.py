from __future__ import annotations

import re


def parse_add_command(text: str) -> tuple[str, str | None]:
    """Разбирает текст команды добавления задачи.

    Ожидается строка с префиксом ``/add`` (как в Telegram). Всё после ``/add``
    — полезная нагрузка. Если в ней есть подстрока ``execute_at``, текст задачи —
    часть слева от **первого** вхождения маркера, дата/время — часть справа
    (после маркера), пробелы по краям обрезаются.

    Примеры корректных входных данных и результатов::

        "/add Купить хлеб"
            -> ("Купить хлеб", None)

        "/add   задача   execute_at   2026-05-11"
            -> ("задача", "2026-05-11")

    Если маркера ``execute_at`` нет, весь хвост после ``/add`` считается текстом
    задачи, второй элемент кортежа — ``None``.
    """
    payload = text[len("/add") :].strip()
    marker = "execute_at"
    if marker in payload:
        left, _, right = payload.partition(marker)
        task_text = left.strip()
        task_date = right.strip() or None
        return task_text, task_date
    return payload, None


def parse_index_numbers(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]
