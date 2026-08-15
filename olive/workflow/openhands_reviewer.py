import json
from pathlib import Path

from openhands.sdk import Agent, Conversation, LLM
from openhands.tools.preset.default import get_default_tools

from olive.state.project import Project
from olive.state.review import Finding, ReviewResult
from olive.workflow.reviewer import Reviewer


class OpenHandsReviewer(Reviewer):
    """Reviewer powered by a local model through OpenHands, with the
    browser tool enabled (unlike OpenHandsExecutor, which disables it).

    Note on model choice: the project spec assumed DeepSeek would fill
    this role, but only qwen3:8b has actually been verified to produce
    reliable OpenHands tool calls in this project's history (see
    FORGE_PROJECT_SPEC.md sec 13) -- DeepSeek has only been exercised
    through plain Ollama chat completions for planning, never through
    OpenHands' tool-calling loop. The default model here is therefore
    qwen3:8b, not deepseek-r1:8b, until DeepSeek's OpenHands tool-calling
    reliability is separately verified.
    """

    def __init__(
        self,
        workspace: Path,
        model: str = "qwen3:8b",
        ollama_base_url: str = "http://localhost:11434",
        review_url: str | None = None,
        persistence_dir: Path | None = None,
    ):
        self.workspace = Path(workspace)
        self.review_url = review_url
        self.persistence_dir = Path(persistence_dir) if persistence_dir else None

        self.llm = LLM(
            model=f"openai/{model}",
            base_url=f"{ollama_base_url}/v1",
            api_key="ollama",
        )

        self.tools = get_default_tools(
            enable_browser=True,
            enable_sub_agents=False,
        )

    def review(self, project: Project) -> ReviewResult:
        agent = Agent(
            llm=self.llm,
            tools=self.tools,
            system_prompt=self._system_prompt(),
        )

        conversation_kwargs = {}
        if self.persistence_dir is not None:
            conversation_kwargs["persistence_dir"] = str(self.persistence_dir)

        conversation = Conversation(
            agent=agent,
            workspace=self.workspace,
            **conversation_kwargs,
        )

        conversation.send_message(self._build_prompt(project))
        conversation.run()

        return self._read_verdict()

    def _build_prompt(self, project: Project) -> str:
        if self.review_url:
            review_target = f"""
A running instance of the application is available at: {self.review_url}
Navigate to it with the browser tool, interact with it, and take
screenshots of anything relevant before forming your verdict.
"""
        else:
            review_target = """
No running application URL was provided -- review the source code in
the workspace instead of a running application.
"""

        requirements = "\n".join(f"- {r}" for r in project.requirements)
        constraints = "\n".join(f"- {c}" for c in project.constraints)

        return f"""
Review the implementation in the current workspace against this
project's requirements and constraints.

# Project
Name: {project.name}
Goal: {project.goal}

## Requirements
{requirements}

## Constraints
{constraints}
{review_target}
Inspect the relevant files (and the running application, if a URL was
given above) and compare what you find against the requirements and
constraints.

When you are done, you MUST write your verdict to review.json in the
workspace root with EXACTLY this structure:

{{
  "approved": true or false,
  "findings": [
    {{"summary": "short description of the issue", "blocking": true or false}}
  ],
  "notes": "a short prose summary of what you reviewed"
}}

Rules:
- approved must be false if any finding has "blocking": true.
- Only include real, concrete findings you actually observed.
- Also write a human-readable review.md summarizing the same review.
- Use the terminal or file_editor tool to actually write both files.
"""

    def _system_prompt(self) -> str:
        return f"""
You are Olive Framework's review and design agent.

You operate on Windows. The terminal is Windows PowerShell.
Never use Linux paths such as /workspace.

Project workspace:
{self.workspace}

Rules:
- Inspect, do not implement. Do not modify source files.
- If a running application URL is given, use the browser tool to visit
  it, interact with it, and take screenshots before forming your verdict.
- Base your verdict only on what you actually observed.
- Always write review.json and review.md as your final action.
"""

    def _read_verdict(self) -> ReviewResult:
        review_path = self.workspace / "review.json"

        if not review_path.exists():
            return ReviewResult(
                approved=False,
                findings=[
                    Finding(
                        summary="Reviewer did not produce review.json",
                        blocking=True,
                    )
                ],
            )

        try:
            data = json.loads(review_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return ReviewResult(
                approved=False,
                findings=[
                    Finding(
                        summary="review.json was not valid JSON",
                        blocking=True,
                    )
                ],
            )

        findings = [
            Finding(
                summary=item.get("summary", ""),
                blocking=item.get("blocking", True),
            )
            for item in data.get("findings", [])
            if isinstance(item, dict)
        ]

        return ReviewResult(
            approved=bool(data.get("approved", False)),
            findings=findings,
            notes=data.get("notes", ""),
        )
