from olive.events import EventBus, EventType
from olive.state.task_graph import TaskGraph
from olive.state.task_state import TaskStatus
from olive.workflow.executor import Executor


class Orchestrator:
    """Execute an Olive Framework task graph."""

    def __init__(
        self,
        graph: TaskGraph,
        executor: Executor,
        events: EventBus | None = None,
    ):
        self.graph = graph
        self.executor = executor
        self.events = events or EventBus()

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
                self.events.publish(
                    EventType.TASK_STARTED,
                    task_id=task.id,
                    title=task.title,
                )

                result = self.executor.execute(task)

                self.statuses[task.id] = result.status

                if result.status == TaskStatus.FAILED:
                    self.events.publish(
                        EventType.TASK_FAILED,
                        task_id=task.id,
                        message=result.message,
                    )
                    raise RuntimeError(
                        f"Task {task.id} failed: "
                        f"{result.message}"
                    )

                self.events.publish(
                    EventType.TASK_COMPLETED,
                    task_id=task.id,
                    message=result.message,
                )
                completed.add(task.id)

        self.events.publish(EventType.ORCHESTRATION_COMPLETED)

    def is_complete(self) -> bool:
        return all(
            status == TaskStatus.COMPLETED
            for status in self.statuses.values()
        )
