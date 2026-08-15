from olive.events import EventBus, EventType
from olive.state.task import Task
from olive.state.task_graph import TaskGraph
from olive.state.task_state import TaskStatus
from olive.orchestrator.engine import Orchestrator
from olive.workflow.fake_executor import FakeExecutor


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
