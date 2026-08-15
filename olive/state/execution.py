from dataclasses import dataclass

from olive.state.task_state import TaskStatus


@dataclass
class TaskExecution:
    task_id: str
    status: TaskStatus
    message: str = ""
