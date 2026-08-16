from olive.events import EventBus, EventType
from olive.state.execution import TaskExecution
from olive.state.task import Task
from olive.state.task_graph import TaskGraph
from olive.state.task_state import TaskStatus
from olive.orchestrator.engine import OrchestrationAborted, Orchestrator
from olive.workflow.executor import Executor
from olive.workflow.fake_executor import FakeExecutor


class ScriptedExecutor(Executor):
    """Fails a given task a fixed number of times before succeeding (or
    forever, if fail_count is None). Every other task succeeds immediately.
    """

    def __init__(self, fail_task_id: str, fail_count: int | None = 1):
        self.fail_task_id = fail_task_id
        self.fail_count = fail_count
        self.attempts: dict[str, int] = {}
        self.executed_tasks: list[str] = []

    def execute(self, task: Task) -> TaskExecution:
        self.executed_tasks.append(task.id)

        if task.id != self.fail_task_id:
            return TaskExecution(
                task_id=task.id, status=TaskStatus.COMPLETED, message="ok"
            )

        self.attempts[task.id] = self.attempts.get(task.id, 0) + 1

        if self.fail_count is None or self.attempts[task.id] <= self.fail_count:
            return TaskExecution(
                task_id=task.id, status=TaskStatus.FAILED, message="boom"
            )

        return TaskExecution(
            task_id=task.id, status=TaskStatus.COMPLETED, message="ok eventually"
        )


def create_graph():
    return TaskGraph(
        tasks=[
            Task(
                id="TASK-001",
                title="Initialize",
                description="Initialize project.",
                task_type="infrastructure",
            ),
            Task(
                id="TASK-002",
                title="Backend",
                description="Build backend.",
                task_type="backend",
                dependencies=["TASK-001"],
            ),
            Task(
                id="TASK-003",
                title="Frontend",
                description="Build frontend.",
                task_type="frontend",
                dependencies=["TASK-001"],
            ),
            Task(
                id="TASK-004",
                title="Integration",
                description="Integrate frontend and backend.",
                task_type="integration",
                dependencies=[
                    "TASK-002",
                    "TASK-003",
                ],
            ),
        ]
    )


def test_orchestrator_executes_all_tasks():
    graph = create_graph()
    executor = FakeExecutor()

    orchestrator = Orchestrator(
        graph=graph,
        executor=executor,
    )

    orchestrator.run()

    assert orchestrator.is_complete()


def test_tasks_execute_in_dependency_order():
    graph = create_graph()
    executor = FakeExecutor()

    orchestrator = Orchestrator(
        graph=graph,
        executor=executor,
    )

    orchestrator.run()

    execution_order = executor.executed_tasks

    assert execution_order.index("TASK-001") < execution_order.index(
        "TASK-002"
    )

    assert execution_order.index("TASK-001") < execution_order.index(
        "TASK-003"
    )

    assert execution_order.index("TASK-002") < execution_order.index(
        "TASK-004"
    )

    assert execution_order.index("TASK-003") < execution_order.index(
        "TASK-004"
    )


def test_all_tasks_are_completed():
    graph = create_graph()
    executor = FakeExecutor()

    orchestrator = Orchestrator(
        graph=graph,
        executor=executor,
    )

    orchestrator.run()

    assert all(
        status == TaskStatus.COMPLETED
        for status in orchestrator.statuses.values()
    )


def test_orchestrator_emits_task_and_completion_events():
    graph = create_graph()
    executor = FakeExecutor()
    events = EventBus()

    orchestrator = Orchestrator(
        graph=graph,
        executor=executor,
        events=events,
    )

    orchestrator.run()

    event_types = [event.type for event in events.log]

    assert event_types.count(EventType.TASK_STARTED) == 4
    assert event_types.count(EventType.TASK_COMPLETED) == 4
    assert event_types[-1] == EventType.ORCHESTRATION_COMPLETED

    for task_id in ("TASK-001", "TASK-002", "TASK-003", "TASK-004"):
        started = event_types.index(
            next(
                e.type
                for e in events.log
                if e.type == EventType.TASK_STARTED
                and e.payload["task_id"] == task_id
            )
        )
        completed_events = [
            i
            for i, e in enumerate(events.log)
            if e.type == EventType.TASK_COMPLETED
            and e.payload["task_id"] == task_id
        ]

        assert completed_events
        assert started < completed_events[0]


def test_orchestrator_creates_its_own_bus_when_none_given():
    graph = create_graph()
    executor = FakeExecutor()

    orchestrator = Orchestrator(graph=graph, executor=executor)
    orchestrator.run()

    assert isinstance(orchestrator.events, EventBus)
    assert EventType.ORCHESTRATION_COMPLETED in [
        event.type for event in orchestrator.events.log
    ]


def test_preseeded_completed_tasks_are_not_re_executed():
    graph = create_graph()
    executor = FakeExecutor()

    orchestrator = Orchestrator(
        graph=graph,
        executor=executor,
        completed={"TASK-001"},
    )
    orchestrator.run()

    assert "TASK-001" not in executor.executed_tasks
    assert set(executor.executed_tasks) == {"TASK-002", "TASK-003", "TASK-004"}
    assert orchestrator.statuses["TASK-001"] == TaskStatus.COMPLETED
    assert orchestrator.is_complete()


def test_all_tasks_preseeded_completed_skips_execution_entirely():
    graph = create_graph()
    executor = FakeExecutor()

    orchestrator = Orchestrator(
        graph=graph,
        executor=executor,
        completed={"TASK-001", "TASK-002", "TASK-003", "TASK-004"},
    )
    orchestrator.run()

    assert executor.executed_tasks == []
    assert orchestrator.is_complete()


def test_a_failing_task_does_not_abort_independent_tasks():
    graph = create_graph()
    executor = ScriptedExecutor(fail_task_id="TASK-002", fail_count=None)

    orchestrator = Orchestrator(graph=graph, executor=executor)
    orchestrator.run()

    # TASK-003 has no dependency on the failing TASK-002, so it still runs.
    assert "TASK-003" in executor.executed_tasks
    assert orchestrator.statuses["TASK-003"] == TaskStatus.COMPLETED


def test_dependents_of_a_failed_task_are_blocked_not_executed():
    graph = create_graph()
    executor = ScriptedExecutor(fail_task_id="TASK-002", fail_count=None)

    orchestrator = Orchestrator(graph=graph, executor=executor)
    orchestrator.run()

    # TASK-004 depends on TASK-002, which never completes.
    assert "TASK-004" not in executor.executed_tasks
    assert orchestrator.statuses["TASK-004"] == TaskStatus.PENDING


def test_failed_task_marks_orchestrator_incomplete_with_failures():
    graph = create_graph()
    executor = ScriptedExecutor(fail_task_id="TASK-002", fail_count=None)

    orchestrator = Orchestrator(graph=graph, executor=executor)
    orchestrator.run()

    assert orchestrator.is_complete() is False
    assert orchestrator.has_failures() is True
    assert orchestrator.failed == {"TASK-002"}


def test_run_does_not_raise_on_task_failure():
    graph = create_graph()
    executor = ScriptedExecutor(fail_task_id="TASK-002", fail_count=None)

    orchestrator = Orchestrator(graph=graph, executor=executor)

    orchestrator.run()  # must not raise


def test_task_retried_up_to_max_retries_then_succeeds():
    graph = create_graph()
    executor = ScriptedExecutor(fail_task_id="TASK-002", fail_count=2)

    orchestrator = Orchestrator(graph=graph, executor=executor, max_retries=2)
    orchestrator.run()

    assert executor.attempts["TASK-002"] == 3
    assert orchestrator.statuses["TASK-002"] == TaskStatus.COMPLETED
    assert orchestrator.is_complete()
    assert orchestrator.has_failures() is False


def test_task_gives_up_after_max_retries_exhausted():
    graph = create_graph()
    executor = ScriptedExecutor(fail_task_id="TASK-002", fail_count=None)

    orchestrator = Orchestrator(graph=graph, executor=executor, max_retries=2)
    orchestrator.run()

    assert executor.attempts["TASK-002"] == 3  # 1 initial + 2 retries
    assert orchestrator.statuses["TASK-002"] == TaskStatus.FAILED
    assert orchestrator.has_failures() is True


def test_retries_emit_task_started_and_task_failed_per_attempt():
    graph = create_graph()
    executor = ScriptedExecutor(fail_task_id="TASK-002", fail_count=None)
    events = EventBus()

    orchestrator = Orchestrator(
        graph=graph, executor=executor, events=events, max_retries=2
    )
    orchestrator.run()

    task_002_started = [
        e
        for e in events.log
        if e.type == EventType.TASK_STARTED and e.payload["task_id"] == "TASK-002"
    ]
    task_002_failed = [
        e
        for e in events.log
        if e.type == EventType.TASK_FAILED and e.payload["task_id"] == "TASK-002"
    ]

    assert [e.payload["attempt"] for e in task_002_started] == [1, 2, 3]
    assert [e.payload["attempt"] for e in task_002_failed] == [1, 2, 3]
    assert [e.payload["retrying"] for e in task_002_failed] == [True, True, False]


def test_orchestration_completed_event_carries_failed_and_blocked():
    graph = create_graph()
    executor = ScriptedExecutor(fail_task_id="TASK-002", fail_count=None)
    events = EventBus()

    orchestrator = Orchestrator(graph=graph, executor=executor, events=events)
    orchestrator.run()

    completion_event = next(
        e for e in events.log if e.type == EventType.ORCHESTRATION_COMPLETED
    )

    assert completion_event.payload["failed"] == ["TASK-002"]
    assert completion_event.payload["blocked"] == ["TASK-004"]


def test_confirm_task_run_executes_normally():
    graph = create_graph()
    executor = FakeExecutor()

    orchestrator = Orchestrator(
        graph=graph, executor=executor, confirm_task=lambda task: "run"
    )
    orchestrator.run()

    assert orchestrator.is_complete()
    assert set(executor.executed_tasks) == {"TASK-001", "TASK-002", "TASK-003", "TASK-004"}


def test_confirm_task_skip_marks_skipped_and_unblocks_dependents():
    graph = create_graph()
    executor = FakeExecutor()

    def confirm(task):
        return "skip" if task.id == "TASK-002" else "run"

    orchestrator = Orchestrator(graph=graph, executor=executor, confirm_task=confirm)
    orchestrator.run()

    assert "TASK-002" not in executor.executed_tasks
    assert orchestrator.statuses["TASK-002"] == TaskStatus.SKIPPED
    assert orchestrator.skipped == {"TASK-002"}
    assert orchestrator.has_skips() is True
    assert orchestrator.is_complete() is False
    assert orchestrator.has_failures() is False
    # TASK-004 depends on TASK-002 (skipped) and TASK-003 -- should still
    # run since skip unblocks dependents just like completion does.
    assert "TASK-004" in executor.executed_tasks


def test_confirm_task_skip_emits_task_skipped_event():
    graph = create_graph()
    executor = FakeExecutor()
    events = EventBus()

    orchestrator = Orchestrator(
        graph=graph,
        executor=executor,
        events=events,
        confirm_task=lambda task: "skip" if task.id == "TASK-001" else "run",
    )
    orchestrator.run()

    skipped_events = [e for e in events.log if e.type == EventType.TASK_SKIPPED]

    assert len(skipped_events) == 1
    assert skipped_events[0].payload["task_id"] == "TASK-001"


def test_confirm_task_abort_raises_before_running_task():
    graph = create_graph()
    executor = FakeExecutor()

    orchestrator = Orchestrator(
        graph=graph, executor=executor, confirm_task=lambda task: "abort"
    )

    import pytest

    with pytest.raises(OrchestrationAborted):
        orchestrator.run()

    assert executor.executed_tasks == []


def test_confirm_task_not_called_for_preseeded_completed_tasks():
    graph = create_graph()
    executor = FakeExecutor()
    calls = []

    def confirm(task):
        calls.append(task.id)
        return "run"

    orchestrator = Orchestrator(
        graph=graph,
        executor=executor,
        completed={"TASK-001"},
        confirm_task=confirm,
    )
    orchestrator.run()

    assert "TASK-001" not in calls
