from pathlib import Path

from olive.state.parser import ProjectParser
from olive.workflow.deepseek_planner import DeepSeekPlanner


PROJECT_FILE = Path("projects/demo/PROJECT.md")


class FakeOllamaClient:
    def chat(self, model, system, prompt):
        assert model == "deepseek-r1:8b"
        assert "local network" in prompt.lower()
        assert "network status dashboard" in prompt.lower()

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
