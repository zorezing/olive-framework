import requests

from olive.state.project import Project
from olive.state.task_graph import TaskGraph
from olive.workflow.ollama_client import OllamaClient
from olive.workflow.planner import Planner
from olive.workflow.planner_output import parse_planner_output
from olive.workflow.prompts import PLANNER_SYSTEM_PROMPT


class DeepSeekPlanner(Planner):
    """Planner powered by a local DeepSeek model through Ollama.

    json_mode note: disabling Ollama's format="json" was tried live as a
    fix for deepseek-r1:8b's slowness, on the theory that grammar-
    constrained decoding was fighting the model's own <think> tokens.
    That theory was wrong: without format="json", this Ollama/model
    combination instead returns a hard 500 ("The model produced output
    that does not match the expected peg-native format") -- a
    server-side template mismatch, not a client-side setting. format="json"
    (the default here) is the only mode that has ever produced usable
    output live, even though it's slow, so it stays the default.
    json_mode is still exposed in case a different Ollama version or
    model doesn't have this quirk.
    """

    def __init__(
        self,
        client: OllamaClient | None = None,
        model: str = "deepseek-r1:8b",
        max_attempts: int = 3,
        json_mode: bool = True,
    ):
        self.client = client or OllamaClient()
        self.model = model
        self.max_attempts = max_attempts
        self.json_mode = json_mode

    def create_plan(self, project: Project) -> TaskGraph:
        prompt = self._build_prompt(project)

        last_error: Exception | None = None

        for _ in range(self.max_attempts):
            try:
                raw_output = self.client.chat(
                    model=self.model,
                    system=PLANNER_SYSTEM_PROMPT,
                    prompt=prompt,
                    json_mode=self.json_mode,
                )

                output = parse_planner_output(raw_output)
                graph = output.to_task_graph()
                graph.validate()
                return graph
            except (ValueError, requests.exceptions.RequestException) as exc:
                last_error = exc

        raise ValueError(
            f"DeepSeek planner produced no valid task graph after "
            f"{self.max_attempts} attempt(s): {last_error}"
        )

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
