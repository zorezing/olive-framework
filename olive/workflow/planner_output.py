import json
import re
from dataclasses import dataclass

from olive.state.task import Task
from olive.state.task_graph import TaskGraph


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCED_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass
class PlannerOutput:
    """Raw structured output returned by a planning model."""

    tasks: list[Task]

    def to_task_graph(self) -> TaskGraph:
        return TaskGraph(tasks=self.tasks)


def _extract_json(raw: str) -> dict:
    """Best-effort extraction of a JSON object from a planner response.

    Reasoning models routinely wrap their answer in <think> blocks,
    markdown code fences, or trailing commentary instead of returning
    bare JSON, even when the request explicitly asks for JSON-only
    output (observed live with deepseek-r1:8b through Ollama).
    """

    candidates = [raw]

    without_think = _THINK_BLOCK.sub("", raw).strip()
    if without_think and without_think != raw:
        candidates.append(without_think)

    fenced = _FENCED_BLOCK.search(without_think or raw)
    if fenced:
        candidates.append(fenced.group(1).strip())

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Last resort: parse the first balanced JSON value found, ignoring
    # any trailing commentary the model kept generating afterward.
    for candidate in candidates:
        start = candidate.find("{")
        if start == -1:
            continue
        try:
            value, _ = json.JSONDecoder().raw_decode(candidate[start:])
            return value
        except json.JSONDecodeError:
            continue

    raise ValueError("Planner output is not valid JSON")


def parse_planner_output(raw: str) -> PlannerOutput:
    """Parse and validate structured planner output."""

    data = _extract_json(raw)

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
