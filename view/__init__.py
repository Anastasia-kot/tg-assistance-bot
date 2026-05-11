from view.print_add_task_confirm import (
    CB_ADD_TASK_NO_PREFIX,
    CB_ADD_TASK_YES_PREFIX,
    print_add_task,
)
from view.print_complete_tasks_confirm import (
    CB_BULK_COMPLETE_NO_PREFIX,
    CB_BULK_COMPLETE_YES_PREFIX,
    print_complete_tasks_confirm,
)
from view.print_delete_tasks_confirm import (
    CB_BULK_DELETE_NO_PREFIX,
    CB_BULK_DELETE_YES_PREFIX,
    print_delete_tasks_confirm,
)
from view.get_list_tasks import (
    get_list_tasks,
    get_list_tasks_html_complete_mark,
    get_list_tasks_html_strike,
)
from view.utils import display_indices_for_task_db_ids
from view.print_list_tasks import (
    print_list_tasks,
    print_list_tasks_with_complete,
    print_list_tasks_with_delete,
)


__all__ = [
    "CB_ADD_TASK_NO_PREFIX",
    "CB_ADD_TASK_YES_PREFIX",
    "CB_BULK_COMPLETE_NO_PREFIX",
    "CB_BULK_COMPLETE_YES_PREFIX",
    "CB_BULK_DELETE_NO_PREFIX",
    "CB_BULK_DELETE_YES_PREFIX",
    "get_list_tasks",
    "display_indices_for_task_db_ids",
    "get_list_tasks_html_complete_mark",
    "get_list_tasks_html_strike",
    "print_add_task",
    "print_list_tasks",
    "print_list_tasks_with_complete",
    "print_complete_tasks_confirm",
    "print_delete_tasks_confirm",
    "print_list_tasks_with_delete",
]
