from olive.state.task_graph import TaskGraph
from olive.state.task_state import TaskStatus
from olive.workflow.executor import Executor


class Orchestrator:
    """Execute an Olive Framework task graph."""

    def __init__(
        self,
        graph: TaskGraph,
        executor: Executor,
    ):
        self.graph = graph
        self.executor = executor

        self.statuses = {
            task.id: TaskStatus.PENDING
            for task in graph.tasks
        }

    def run(self) -> None:
        """Execute all tasks whose dependencies are satisfied."""

        completed = set()

        while len(completed) < len(self.graph.tasks):
            ready_tasks = self.graph.ready_tasks(completed)

            if not ready_tasks:
                raise RuntimeError(
                    "No executable tasks remain. "
                    "The task graph may contain an unresolved dependency."
                )

            for task in ready_tasks:
                self.statuses[task.id] = TaskStatus.RUNNING

                result = self.executor.execute(task)

                self.statuses[task.id] = result.status

                if result.status == TaskStatus.FAILED:
                    raise RuntimeError(
                        f"Task {task.id} failed: "
                        f"{result.message}"
                    )

                completed.add(task.id)

    def is_complete(self) -> bool:
        return all(
            status == TaskStatus.COMPLETED
            for status in self.statuses.values()
        )
