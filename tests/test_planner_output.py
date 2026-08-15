import json

import pytest

from olive.workflow.planner_output import parse_planner_output


def valid_output():
    return json.dumps(
        {
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "Initialize project",
                    "description": "Create the project structure.",
                    "task_type": "infrastructure",
                    "dependencies": [],
                },
                {
                    "id": "TASK-002",
                    "title": "Create backend",
                    "description": "Create the backend.",
                    "task_type": "backend",
                    "dependencies": ["TASK-001"],
                },
            ]
        }
    )


def test_valid_planner_output():
    output = parse_planner_output(valid_output())

    assert len(output.tasks) == 2
    assert output.tasks[1].dependencies == ["TASK-001"]


def test_planner_output_wrapped_in_markdown_fence():
    raw = f"```json\n{valid_output()}\n```"

    output = parse_planner_output(raw)

    assert len(output.tasks) == 2


def test_planner_output_with_leading_think_block():
    raw = f"<think>\nLet me plan this out...\n</think>\n{valid_output()}"

    output = parse_planner_output(raw)

    assert len(output.tasks) == 2


def test_planner_output_with_trailing_commentary_after_json():
    raw = f"{valid_output()}\n\nI think that covers everything, let me also consider..."

    output = parse_planner_output(raw)

    assert len(output.tasks) == 2


def test_planner_output_fenced_with_stray_closing_think_tag():
    # Matches an actual deepseek-r1:8b response observed live: JSON wrapped
    # in a fence, immediately followed by a stray "</think>" and then more
    # (unrelated, ignored) rambling.
    raw = f"\n```json\n{valid_output()}\n```</think>\nSome more unrelated text and even another {{ incomplete block"

    output = parse_planner_output(raw)

    assert len(output.tasks) == 2


def test_planner_output_becomes_task_graph():
    output = parse_planner_output(valid_output())

    graph = output.to_task_graph()

    graph.validate()

    assert graph.get_task("TASK-002").title == "Create backend"


def test_invalid_json():
    with pytest.raises(ValueError, match="valid JSON"):
        parse_planner_output("this isn't json")


def test_missing_tasks():
    raw = json.dumps({})

    with pytest.raises(ValueError, match="tasks"):
        parse_planner_output(raw)


def test_tasks_must_be_list():
    raw = json.dumps(
        {
            "tasks": {}
        }
    )

    with pytest.raises(ValueError):
        parse_planner_output(raw)


def test_missing_task_field():
    raw = json.dumps(
        {
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "Something",
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="missing fields"):
        parse_planner_output(raw)


def test_unknown_dependency():
    raw = json.dumps(
        {
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "Backend",
                    "description": "Create backend.",
                    "task_type": "backend",
                    "dependencies": ["TASK-999"],
                }
            ]
        }
    )

    output = parse_planner_output(raw)
    graph = output.to_task_graph()

    with pytest.raises(ValueError, match="unknown task"):
        graph.validate()


def test_duplicate_task_ids():
    raw = json.dumps(
        {
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "First",
                    "description": "First task.",
                    "task_type": "backend",
                    "dependencies": [],
                },
                {
                    "id": "TASK-001",
                    "title": "Second",
                    "description": "Second task.",
                    "task_type": "frontend",
                    "dependencies": [],
                },
            ]
        }
    )

    output = parse_planner_output(raw)
    graph = output.to_task_graph()

    with pytest.raises(ValueError, match="duplicate"):
        graph.validate()


def test_self_dependency():
    raw = json.dumps(
        {
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "Impossible task",
                    "description": "Invalid dependency.",
                    "task_type": "backend",
                    "dependencies": ["TASK-001"],
                }
            ]
        }
    )

    output = parse_planner_output(raw)
    graph = output.to_task_graph()

    with pytest.raises(ValueError, match="itself"):
        graph.validate()


def test_circular_dependency():
    raw = json.dumps(
        {
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "First",
                    "description": "First task.",
                    "task_type": "backend",
                    "dependencies": ["TASK-002"],
                },
                {
                    "id": "TASK-002",
                    "title": "Second",
                    "description": "Second task.",
                    "task_type": "backend",
                    "dependencies": ["TASK-001"],
                },
            ]
        }
    )

    output = parse_planner_output(raw)
    graph = output.to_task_graph()

    with pytest.raises(ValueError, match="circular"):
        graph.validate()
