from olive.state.project import Project
from olive.state.task_graph import TaskGraph
from olive.workflow.ollama_client import OllamaClient
from olive.workflow.planner import Planner
from olive.workflow.planner_output import parse_planner_output
from olive.workflow.prompts import PLANNER_SYSTEM_PROMPT


class DeepSeekPlanner(Planner):
    """Planner powered by a local DeepSeek model through Ollama."""

    def __init__(
        self,
        client: OllamaClient | None = None,
        model: str = "deepseek-r1:8b",
    ):
        self.client = client or OllamaClient()
        self.model = model

    def create_plan(self, project: Project) -> TaskGraph:
        prompt = self._build_prompt(project)

        raw_output = self.client.chat(
            model=self.model,
            system=PLANNER_SYSTEM_PROMPT,
            prompt=prompt,
        )

        output = parse_planner_output(raw_output)

        graph = output.to_task_graph()
        graph.validate()

        return graph

    @staticmethod
    def _build_prompt(project: Project) -> str:
        requirements = "\n".join(
            f"- {item}"
            for item in project.requirements
        )

        constraints = "\n".join(
            f"- {item}"
            for item in project.constraints
        )

        return f"""
# Project

Name:
{project.name}

## Goal

{project.goal}

## Requirements

{requirements}

## Constraints

{constraints}

Analyze this project and create the implementation task graph.

Remember:
- Only return the JSON required by the system instructions.
- Create concrete, executable tasks.
- Establish correct dependencies.
- Do not write implementation code.
"""
