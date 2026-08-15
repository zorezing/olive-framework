from olive.state.execution import TaskExecution
from olive.state.task import Task
from olive.state.task_state import TaskStatus
from olive.workflow.executor import Executor


class FakeExecutor(Executor):
    """Deterministic executor used for testing."""

    def __init__(self):
        self.executed_tasks: list[str] = []

    def execute(self, task: Task) -> TaskExecution:
        self.executed_tasks.append(task.id)

        return TaskExecution(
            task_id=task.id,
            status=TaskStatus.COMPLETED,
            message=f"Completed {task.id}",
        )
