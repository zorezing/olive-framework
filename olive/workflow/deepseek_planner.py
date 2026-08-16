import requests

from olive.state.project import Project
from olive.state.task_graph import TaskGraph
from olive.workflow.ollama_client import OllamaClient
from olive.workflow.planner import Planner
from olive.workflow.planner_output import parse_planner_output
from olive.workflow.prompts import PLANNER_SYSTEM_PROMPT


class DeepSeekPlanner(Planner):
    """Chat-completion-based planner, driven by a local model through
    Ollama. Named for the model the project spec originally envisioned
    for this role, but the model is fully configurable -- and, based on
    live testing, deepseek-r1:8b is *not* the reliable choice on modest
    hardware (see below), so it is no longer the default.

    Live reliability findings on this project's development machine
    (RTX 4050 6GB, per FORGE_PROJECT_SPEC.md secs 17-19):

    - deepseek-r1:8b generated 335 reasoning tokens for the trivial
      prompt "ping" alone, at roughly 10 tokens/sec. On the real planner
      prompt it either took ~15 minutes and produced content with a
      duplicate task ID, or did not respond within 30 minutes at all,
      across repeated attempts.
    - qwen3:8b -- already the only model verified reliable for OpenHands
      tool-calling in this project (FORGE_PROJECT_SPEC.md sec 13) -- was
      tested against the identical real planner prompt and returned a
      clean, fully valid 15-task plan in ~3m15s with zero retries needed.

    qwen3:8b is therefore the default model here. deepseek-r1:8b remains
    available by passing model="deepseek-r1:8b" explicitly, for anyone
    running on hardware that can push tokens/sec high enough to make its
    much longer reasoning traces practical.

    json_mode note: disabling Ollama's format="json" was tried live as a
    separate fix for the slowness, on the theory that grammar-constrained
    decoding was fighting <think> tokens. That theory was wrong: Ollama
    0.32.6 already separates thinking from content correctly even with
    format="json" (confirmed live), and disabling it for deepseek-r1:8b
    instead produced a hard 500 ("output does not match the expected
    peg-native format") -- a server-side template mismatch. format="json"
    stays on by default.
    """

    def __init__(
        self,
        client: OllamaClient | None = None,
        model: str = "qwen3:8b",
        max_attempts: int = 3,
        json_mode: bool = True,
        num_predict: int | None = 4096,
    ):
        self.client = client or OllamaClient()
        self.model = model
        self.max_attempts = max_attempts
        self.json_mode = json_mode
        self.num_predict = num_predict

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
                    num_predict=self.num_predict,
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
