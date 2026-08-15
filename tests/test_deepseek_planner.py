from pathlib import Path

from olive.state.parser import ProjectParser
from olive.workflow.deepseek_planner import DeepSeekPlanner


PROJECT_FILE = Path("projects/demo/PROJECT.md")


class FakeOllamaClient:
    def chat(self, model, system, prompt, json_mode=True):
        assert model == "deepseek-r1:8b"
        assert "local network" in prompt.lower()
        assert "network status dashboard" in prompt.lower()
        assert json_mode is True

        return """
        {
          "tasks": [
            {
              "id": "TASK-001",
              "title": "Initialize project",
              "description": "Create the initial project structure.",
              "task_type": "infrastructure",
              "dependencies": []
            },
            {
              "id": "TASK-002",
              "title": "Create backend",
              "description": "Create the FastAPI backend.",
              "task_type": "backend",
              "dependencies": ["TASK-001"]
            }
          ]
        }
        """


def test_deepseek_planner():
    project = ProjectParser().parse(PROJECT_FILE)

    planner = DeepSeekPlanner(
        client=FakeOllamaClient()
    )

    graph = planner.create_plan(project)

    assert len(graph.tasks) == 2
    assert graph.get_task("TASK-001").title == "Initialize project"
    assert graph.get_task("TASK-002").dependencies == [
        "TASK-001"
    ]


VALID_RESPONSE = """
{
  "tasks": [
    {
      "id": "TASK-001",
      "title": "Initialize project",
      "description": "Create the initial project structure.",
      "task_type": "infrastructure",
      "dependencies": []
    }
  ]
}
"""

DUPLICATE_ID_RESPONSE = """
{
  "tasks": [
    {
      "id": "TASK-001",
      "title": "First",
      "description": "First task.",
      "task_type": "backend",
      "dependencies": []
    },
    {
      "id": "TASK-001",
      "title": "Duplicate",
      "description": "Same ID as the first task.",
      "task_type": "backend",
      "dependencies": []
    }
  ]
}
"""


class FlakyOllamaClient:
    """Returns bad output for the first N calls, then a valid plan.

    Mirrors what was observed live with deepseek-r1:8b: some generations
    fail validation (e.g. duplicate task IDs) even though the request
    asked for a single clean plan.
    """

    def __init__(self, bad_responses: list[str]):
        self.bad_responses = list(bad_responses)
        self.calls = 0

    def chat(self, model, system, prompt, json_mode=True):
        assert json_mode is True
        self.calls += 1

        if self.bad_responses:
            return self.bad_responses.pop(0)

        return VALID_RESPONSE


def test_deepseek_planner_retries_after_invalid_json():
    project = ProjectParser().parse(PROJECT_FILE)

    client = FlakyOllamaClient(bad_responses=["not json at all"])
    planner = DeepSeekPlanner(client=client, max_attempts=3)

    graph = planner.create_plan(project)

    assert client.calls == 2
    assert len(graph.tasks) == 1


def test_deepseek_planner_retries_after_failed_validation():
    project = ProjectParser().parse(PROJECT_FILE)

    client = FlakyOllamaClient(bad_responses=[DUPLICATE_ID_RESPONSE])
    planner = DeepSeekPlanner(client=client, max_attempts=3)

    graph = planner.create_plan(project)

    assert client.calls == 2
    assert len(graph.tasks) == 1


def test_deepseek_planner_gives_up_after_max_attempts():
    import pytest

    project = ProjectParser().parse(PROJECT_FILE)

    client = FlakyOllamaClient(
        bad_responses=[DUPLICATE_ID_RESPONSE, DUPLICATE_ID_RESPONSE, DUPLICATE_ID_RESPONSE]
    )
    planner = DeepSeekPlanner(client=client, max_attempts=3)

    with pytest.raises(ValueError, match="3 attempt"):
        planner.create_plan(project)

    assert client.calls == 3


def test_json_mode_defaults_to_true():
    planner = DeepSeekPlanner(client=FakeOllamaClient())

    assert planner.json_mode is True


def test_json_mode_can_be_overridden():
    planner = DeepSeekPlanner(client=FakeOllamaClient(), json_mode=False)

    assert planner.json_mode is False


class RaisingThenValidOllamaClient:
    """Raises a network-level exception for the first N calls, then
    returns a valid plan. Verifies retries also cover transient HTTP/
    network failures (timeouts, 500s), not just bad JSON content --
    observed live as a real failure mode with deepseek-r1:8b.
    """

    def __init__(self, exceptions: list[Exception]):
        self.exceptions = list(exceptions)
        self.calls = 0

    def chat(self, model, system, prompt, json_mode=True):
        self.calls += 1

        if self.exceptions:
            raise self.exceptions.pop(0)

        return VALID_RESPONSE


def test_deepseek_planner_retries_after_request_exception():
    import requests

    project = ProjectParser().parse(PROJECT_FILE)

    client = RaisingThenValidOllamaClient(
        exceptions=[requests.exceptions.ReadTimeout("timed out")]
    )
    planner = DeepSeekPlanner(client=client, max_attempts=3)

    graph = planner.create_plan(project)

    assert client.calls == 2
    assert len(graph.tasks) == 1


def test_deepseek_planner_gives_up_after_repeated_request_exceptions():
    import pytest
    import requests

    project = ProjectParser().parse(PROJECT_FILE)

    client = RaisingThenValidOllamaClient(
        exceptions=[
            requests.exceptions.HTTPError("500"),
            requests.exceptions.HTTPError("500"),
            requests.exceptions.HTTPError("500"),
        ]
    )
    planner = DeepSeekPlanner(client=client, max_attempts=3)

    with pytest.raises(ValueError, match="3 attempt"):
        planner.create_plan(project)

    assert client.calls == 3
