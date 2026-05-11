from view.utils import format_execute_at


def print_list_tasks(bot, message, rows) -> None:
    if not rows:
        bot.send_message(message.chat.id, text="Список задач пуст.")
        return

    done_mark = "✅"
    block_sep = "───────────────"
    lines: list[str] = []
    pending_block_started = False
    for idx, (_, text, is_completed, execute_at) in enumerate(rows, start=1):
        if not is_completed and not pending_block_started:
            pending_block_started = True
            if lines:
                lines.append(block_sep)
        due = format_execute_at(execute_at)
        due_part = f" ({due})" if due else ""
        lines.append(f"{idx}. {text}{due_part}" + (f" {done_mark}" if is_completed else ""))

    bot.send_message(message.chat.id, text="\n".join(lines))
