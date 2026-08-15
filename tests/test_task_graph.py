from olive.state.task import Task
from olive.state.task_graph import TaskGraph


def make_graph():
    return TaskGraph(
        tasks=[
            Task(
                id="TASK-001",
                title="Initialize project",
                description="Create the project structure.",
                task_type="infrastructure",
            ),
            Task(
                id="TASK-002",
                title="Create backend",
                description="Create the backend application.",
                task_type="backend",
                dependencies=["TASK-001"],
            ),
            Task(
                id="TASK-003",
                title="Create frontend",
                description="Create the frontend application.",
                task_type="frontend",
                dependencies=["TASK-001"],
            ),
            Task(
                id="TASK-004",
                title="Connect frontend",
                description="Connect frontend to backend.",
                task_type="integration",
                dependencies=[
                    "TASK-002",
                    "TASK-003",
                ],
            ),
        ]
    )


def test_task_lookup():
    graph = make_graph()

    task = graph.get_task("TASK-002")

    assert task.title == "Create backend"


def test_task_ids():
    graph = make_graph()

    assert graph.task_ids() == {
        "TASK-001",
        "TASK-002",
        "TASK-003",
        "TASK-004",
    }


def test_initial_ready_task():
    graph = make_graph()

    ready = graph.ready_tasks(set())

    assert [task.id for task in ready] == ["TASK-001"]


def test_backend_and_frontend_ready_after_initialization():
    graph = make_graph()

    ready = graph.ready_tasks({"TASK-001"})

    assert {task.id for task in ready} == {
        "TASK-002",
        "TASK-003",
    }


def test_integration_waits_for_dependencies():
    graph = make_graph()

    ready = graph.ready_tasks(
        {
            "TASK-001",
            "TASK-002",
        }
    )

    assert [task.id for task in ready] == ["TASK-003"]


def test_integration_becomes_ready():
    graph = make_graph()

    ready = graph.ready_tasks(
        {
            "TASK-001",
            "TASK-002",
            "TASK-003",
        }
    )

    assert [task.id for task in ready] == ["TASK-004"]
