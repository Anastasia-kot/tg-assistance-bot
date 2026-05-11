_pending_tasks: dict[str, dict] = {}


def set_pending_task(token: str, payload: dict) -> None:
    _pending_tasks[token] = payload


def pop_pending_task(token: str) -> dict | None:
    return _pending_tasks.pop(token, None)
