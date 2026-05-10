from __future__ import annotations

import re


def parse_add_command(text: str) -> tuple[str, str | None]:
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
