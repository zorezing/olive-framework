from typing import Callable

from olive.events import EventBus, EventType
from olive.state.task import Task
from olive.state.task_graph import TaskGraph
from olive.state.task_state import TaskStatus
from olive.workflow.executor import Executor


class OrchestrationAborted(Exception):
    """Raised when confirm_task returns "abort", stopping run() early."""


class Orchestrator:
    """Execute an Olive Framework task graph."""

    def __init__(
        self,
        graph: TaskGraph,
        executor: Executor,
        events: EventBus | None = None,
        completed: set[str] | None = None,
        max_retries: int = 0,
        confirm_task: Callable[[Task], str] | None = None,
    ):
        self.graph = graph
        self.executor = executor
        self.events = events or EventBus()
        self._preseeded_completed = set(completed or ())
        self.max_retries = max_retries
        self.confirm_task = confirm_task
        self.failed: set[str] = set()
        self.skipped: set[str] = set()

        self.statuses = {
            task.id: (
                TaskStatus.COMPLETED
                if task.id in self._preseeded_completed
                else TaskStatus.PENDING
            )
            for task in graph.tasks
        }

    def run(self) -> None:
        """Execute all tasks whose dependencies are satisfied.

        Tasks whose IDs were passed in as already ``completed`` (e.g.
        resumed from persisted state) are skipped rather than re-executed.

        A task that fails is retried up to ``max_retries`` times before
        being marked FAILED for good. A permanently failed task does not
        abort the run: independent tasks keep executing, and only tasks
        that (transitively) depend on the failure are left BLOCKED
        (PENDING, never becoming ready). Check ``failed`` / ``is_complete``
        after ``run()`` returns to see what happened.

        If ``confirm_task`` was given, it's called with each task right
        before it would run, and must return "run", "skip", or "abort".
        A skipped task is marked SKIPPED (distinct from COMPLETED --
        ``is_complete()`` is false, ``has_skips()`` is true) but still
        unblocks dependents, on the assumption a human skipped it because
        it was already handled some other way. "abort" raises
        OrchestrationAborted immediately, before that task runs.
        """

        completed = set(self._preseeded_completed)

        while True:
            ready_tasks = [
                task
                for task in self.graph.ready_tasks(completed)
                if task.id not in self.failed
            ]

            if not ready_tasks:
                break

            for task in ready_tasks:
                if self.confirm_task is not None:
                    decision = self.confirm_task(task)

                    if decision == "abort":
                        raise OrchestrationAborted(
                            f"Aborted before running {task.id}"
                        )

                    if decision == "skip":
                        self.statuses[task.id] = TaskStatus.SKIPPED
                        self.skipped.add(task.id)
                        self.events.publish(
                            EventType.TASK_SKIPPED, task_id=task.id
                        )
                        completed.add(task.id)
                        continue

                result = self._execute_with_retries(task)

                self.statuses[task.id] = result.status

                if result.status == TaskStatus.FAILED:
                    self.failed.add(task.id)
                else:
                    self.events.publish(
                        EventType.TASK_COMPLETED,
                        task_id=task.id,
                        message=result.message,
                    )
                    completed.add(task.id)

        if self.failed:
            blocked = self.graph.task_ids() - completed - self.failed
            self.events.publish(
                EventType.ORCHESTRATION_COMPLETED,
                failed=sorted(self.failed),
                blocked=sorted(blocked),
            )
        else:
            self.events.publish(EventType.ORCHESTRATION_COMPLETED)

    def _execute_with_retries(self, task):
        attempt = 0

        while True:
            attempt += 1
            self.statuses[task.id] = TaskStatus.RUNNING
            self.events.publish(
                EventType.TASK_STARTED,
                task_id=task.id,
                title=task.title,
                attempt=attempt,
            )

            result = self.executor.execute(task)

            if result.status != TaskStatus.FAILED:
                return result

            retrying = attempt <= self.max_retries
            self.events.publish(
                EventType.TASK_FAILED,
                task_id=task.id,
                message=result.message,
                attempt=attempt,
                retrying=retrying,
            )

            if not retrying:
                return result

    def is_complete(self) -> bool:
        return all(
            status == TaskStatus.COMPLETED
            for status in self.statuses.values()
        )

    def has_failures(self) -> bool:
        return bool(self.failed)

    def has_skips(self) -> bool:
        return bool(self.skipped)
