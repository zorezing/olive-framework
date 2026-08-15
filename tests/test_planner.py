from pathlib import Path

from olive.state.parser import ProjectParser
from olive.workflow.mock_planner import MockPlanner


PROJECT_FILE = Path("projects/demo/PROJECT.md")


def test_mock_planner_creates_task_graph():
    project = ProjectParser().parse(PROJECT_FILE)

    planner = MockPlanner()

    graph = planner.create_plan(project)

    assert len(graph.tasks) == 3


def test_mock_planner_creates_dependencies():
    project = ProjectParser().parse(PROJECT_FILE)

    planner = MockPlanner()

    graph = planner.create_plan(project)

    task_2 = graph.get_task("TASK-002")
    task_3 = graph.get_task("TASK-003")

    assert task_2.dependencies == ["TASK-001"]
    assert task_3.dependencies == ["TASK-002"]


def test_planner_receives_project_information():
    project = ProjectParser().parse(PROJECT_FILE)

    planner = MockPlanner()

    graph = planner.create_plan(project)

    first_task = graph.get_task("TASK-001")

    assert project.name in first_task.description


def test_mock_plan_can_execute_in_order():
    project = ProjectParser().parse(PROJECT_FILE)

    planner = MockPlanner()

    graph = planner.create_plan(project)

    completed = set()

    ready = graph.ready_tasks(completed)
    assert [task.id for task in ready] == ["TASK-001"]

    completed.add("TASK-001")

    ready = graph.ready_tasks(completed)
    assert [task.id for task in ready] == ["TASK-002"]

    completed.add("TASK-002")

    ready = graph.ready_tasks(completed)
    assert [task.id for task in ready] == ["TASK-003"]
