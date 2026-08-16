from pathlib import Path

import requests

from olive.state.project import Project
from olive.state.review import Finding, ReviewResult
from olive.workflow.json_extraction import extract_json
from olive.workflow.ollama_client import OllamaClient
from olive.workflow.reviewer import Reviewer


REVIEWER_SYSTEM_PROMPT = """
You are Olive Framework's review agent. You are given a project's
requirements/constraints and the contents of its implementation files.
Compare them and return ONLY valid JSON with this exact structure:

{
  "approved": true or false,
  "findings": [
    {"summary": "short description of the issue", "blocking": true or false}
  ],
  "notes": "a short prose summary of what you reviewed"
}

Rules:
- approved must be false if any finding has "blocking": true.
- Only include real, concrete findings backed by the file contents shown
  to you. Do not invent issues you have no evidence for.
- Do not include markdown fences or explanations outside the JSON.
"""

_SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    ".venv312",
    ".olive",
    ".pytest_cache",
}


class SimpleReviewer(Reviewer):
    """Reviews a workspace's source files against a project's requirements
    via a single Ollama chat completion -- no agentic tool-calling loop.

    Built after OpenHandsReviewer (agentic, tool-calling) proved
    unreliable live with qwen3:8b for this multi-step task: across five
    live attempts it variously hallucinated tool call parameters,
    reasoned about files hypothetically without ever calling a tool to
    read them, or (most persistently, even with explicit "you are
    autonomous, no one will answer" framing at both the system and task
    prompt level) stopped after a single tool call to ask what to do
    next. This class instead mirrors what has been reliable all along
    for the Ollama-backed planner: read the files in plain Python, then
    one bounded chat completion in, one JSON verdict out -- no
    multi-turn agentic decision-making for the model to get lost in.

    Use this for source-code review (no running application to visit).
    Browser-based visual review of a running app still needs
    OpenHandsReviewer, since there's no way around requiring an agent
    with browser tools for that.
    """

    def __init__(
        self,
        workspace: Path,
        client: OllamaClient | None = None,
        model: str = "qwen3:8b",
        max_attempts: int = 3,
        max_files: int = 40,
        max_file_chars: int = 20_000,
    ):
        self.workspace = Path(workspace)
        self.client = client or OllamaClient()
        self.model = model
        self.max_attempts = max_attempts
        self.max_files = max_files
        self.max_file_chars = max_file_chars

    def review(self, project: Project) -> ReviewResult:
        prompt = self._build_prompt(project)

        last_error: Exception | None = None

        for _ in range(self.max_attempts):
            try:
                raw_output = self.client.chat(
                    model=self.model,
                    system=REVIEWER_SYSTEM_PROMPT,
                    prompt=prompt,
                    json_mode=True,
                    num_predict=2048,
                )
                return self._parse_verdict(raw_output)
            except (ValueError, requests.exceptions.RequestException) as exc:
                last_error = exc

        return ReviewResult(
            approved=False,
            findings=[
                Finding(
                    summary=(
                        "Reviewer failed to produce a valid verdict after "
                        f"{self.max_attempts} attempt(s): {last_error}"
                    ),
                    blocking=True,
                )
            ],
        )

    def _collect_files(self) -> str:
        entries = []

        for path in sorted(self.workspace.rglob("*")):
            if len(entries) >= self.max_files:
                break
            if path.is_dir():
                continue
            if any(part in _SKIP_DIR_NAMES for part in path.parts):
                continue
            if path.name in ("review.json", "review.md"):
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            relative = path.relative_to(self.workspace)
            truncated = text[: self.max_file_chars]
            entries.append(f"### {relative}\n```\n{truncated}\n```")

        return "\n\n".join(entries) if entries else "(no readable files found)"

    def _build_prompt(self, project: Project) -> str:
        requirements = "\n".join(f"- {r}" for r in project.requirements)
        constraints = "\n".join(f"- {c}" for c in project.constraints)
        files_blob = self._collect_files()

        return f"""
# Project
Name: {project.name}
Goal: {project.goal}

## Requirements
{requirements}

## Constraints
{constraints}

# Workspace files

{files_blob}

Review the files above against the requirements and constraints. Return
ONLY the JSON verdict described in the system instructions.
"""

    def _parse_verdict(self, raw: str) -> ReviewResult:
        data = extract_json(raw)

        if not isinstance(data, dict):
            raise ValueError("Reviewer output must be a JSON object")

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
