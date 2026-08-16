from dataclasses import dataclass

from olive.state.task import Task
from olive.state.task_graph import TaskGraph
from olive.workflow.json_extraction import extract_json


@dataclass
class PlannerOutput:
    """Raw structured output returned by a planning model."""

    tasks: list[Task]

    def to_task_graph(self) -> TaskGraph:
        return TaskGraph(tasks=self.tasks)


def parse_planner_output(raw: str) -> PlannerOutput:
    """Parse and validate structured planner output."""

    try:
        data = extract_json(raw)
    except ValueError as exc:
        raise ValueError("Planner output is not valid JSON") from exc

    if not isinstance(data, dict):
        raise ValueError(
            "Planner output must be a JSON object"
        )

    if "tasks" not in data:
        raise ValueError(
            "Planner output must contain a 'tasks' field"
        )

    if not isinstance(data["tasks"], list):
        raise ValueError(
            "'tasks' must be a list"
        )

    tasks = []

    for index, item in enumerate(data["tasks"]):
        if not isinstance(item, dict):
            raise ValueError(
                f"Task {index} must be an object"
            )

        required_fields = {
            "id",
            "title",
            "description",
            "task_type",
            "dependencies",
        }

        missing = required_fields - item.keys()

        if missing:
            raise ValueError(
                f"Task {index} is missing fields: "
                f"{sorted(missing)}"
            )

        if not isinstance(item["id"], str):
            raise ValueError(
                f"Task {index} id must be a string"
            )

        if not isinstance(item["title"], str):
            raise ValueError(
                f"Task {index} title must be a string"
            )

        if not isinstance(item["description"], str):
            raise ValueError(
                f"Task {index} description must be a string"
            )

        if not isinstance(item["task_type"], str):
            raise ValueError(
                f"Task {index} task_type must be a string"
            )

        if not isinstance(item["dependencies"], list):
            raise ValueError(
                f"Task {index} dependencies must be a list"
            )

        if not all(
            isinstance(dependency, str)
            for dependency in item["dependencies"]
        ):
            raise ValueError(
                f"Task {index} dependencies must contain "
                "only strings"
            )

        tasks.append(
            Task(
                id=item["id"],
                title=item["title"],
                description=item["description"],
                task_type=item["task_type"],
                dependencies=item["dependencies"],
            )
        )

    return PlannerOutput(tasks=tasks)
