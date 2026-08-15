import json
from pathlib import Path

from olive.workflow.planner_output import parse_planner_output


def test_realistic_planner_response():
    path = Path("tests/fixtures/planner_response.json")

    raw = path.read_text(encoding="utf-8")

    output = parse_planner_output(raw)
    graph = output.to_task_graph()

    graph.validate()

    assert len(graph.tasks) == 7

    ready = graph.ready_tasks(set())

    assert [task.id for task in ready] == ["TASK-001"]
