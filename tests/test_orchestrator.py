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
