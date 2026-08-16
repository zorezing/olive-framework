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
        max_attempts: int = 3,
    ):
        self.workspace = Path(workspace)
        self.review_url = review_url
        self.persistence_dir = Path(persistence_dir) if persistence_dir else None
        self.max_attempts = max_attempts

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
        """Run the review conversation, retrying up to max_attempts times
        if the agent fails to produce a valid review.json.

        This is a mechanism-failure retry, not a content-based one: a
        legitimately produced review.json with approved=false is returned
        immediately, never retried. Only a missing/malformed review.json
        (the agent got stuck mid-tool-call, hallucinated a nonexistent
        tool, etc. -- both observed live with qwen3:8b) triggers a retry,
        each with a fresh conversation so a bad trajectory isn't repeated
        deterministically.
        """

        for attempt in range(1, self.max_attempts + 1):
            self._clear_stale_verdict()
            self._run_conversation(project, attempt)

            result = self._read_verdict()
            if result is not None:
                return result

        return ReviewResult(
            approved=False,
            findings=[
                Finding(
                    summary=(
                        "Reviewer did not produce a valid review.json "
                        f"after {self.max_attempts} attempt(s)"
                    ),
                    blocking=True,
                )
            ],
        )

    def _clear_stale_verdict(self) -> None:
        """Remove any review.json/review.md left over from a previous run
        in this workspace, so a fully-failed attempt can't be mistaken for
        success by reading stale output that was never produced this time.
        """

        for name in ("review.json", "review.md"):
            path = self.workspace / name
            if path.exists():
                path.unlink()

    def _run_conversation(self, project: Project, attempt: int) -> None:
        agent = Agent(
            llm=self.llm,
            tools=self.tools,
            system_prompt=self._system_prompt(),
        )

        conversation_kwargs = {}
        if self.persistence_dir is not None:
            conversation_kwargs["persistence_dir"] = str(
                self.persistence_dir / f"attempt-{attempt}"
            )

        conversation = Conversation(
            agent=agent,
            workspace=self.workspace,
            **conversation_kwargs,
        )

        conversation.send_message(self._build_prompt(project))
        conversation.run()

    def _build_prompt(self, project: Project) -> str:
        steps = [
            "Use the terminal tool (e.g. `Get-ChildItem`) to list the "
            "files in the workspace.",
            "Use the terminal tool (e.g. `Get-Content`) to read the "
            "actual contents of every file relevant to the requirements "
            "and constraints below.",
        ]

        if self.review_url:
            steps.append(
                f"Use the browser tool to navigate to {self.review_url}, "
                "interact with the application, and take screenshots."
            )
            observed_steps = "1-3"
        else:
            observed_steps = "1-2"

        steps.append(
            "Compare what you actually observed above against every "
            "requirement and constraint. Note concrete discrepancies."
        )
        steps.append(
            "Write your verdict to review.json in the workspace root "
            "with EXACTLY this structure, using the terminal tool with "
            "a PowerShell here-string -- do not use the file_editor "
            "tool for this:\n\n"
            "$json = @'\n"
            "{\n"
            '  "approved": true or false,\n'
            '  "findings": [\n'
            '    {"summary": "short description of the issue", '
            '"blocking": true or false}\n'
            "  ],\n"
            '  "notes": "a short prose summary of what you reviewed"\n'
            "}\n"
            "'@\n"
            "Set-Content -Path review.json -Value $json"
        )
        steps.append(
            "Write a human-readable review.md summarizing the same "
            "review, the same way (a PowerShell here-string with "
            "Set-Content)."
        )

        numbered_steps = "\n".join(
            f"Step {i}: {step}" for i, step in enumerate(steps, start=1)
        )

        if self.review_url:
            review_target = (
                f"A running instance of the application is available at: "
                f"{self.review_url}\n"
            )
        else:
            review_target = (
                "No running application URL was provided -- review the "
                "source code in the workspace instead of a running "
                "application.\n"
            )

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
Complete every step below yourself, one tool call after another,
without stopping to ask what to do next -- no one will answer. Follow
these steps in order. Actually call the tools at each step -- never
assume, guess, or simulate what a file contains or what the
application does. If you have not called a tool to look at something,
you do not know it.

{numbered_steps}

Rules:
- approved must be false if any finding has "blocking": true.
- Only include real, concrete findings backed by something you actually
  read or observed in steps {observed_steps} above.
- Do not skip straight to writing the verdict -- you must call the
  terminal tool at least once to inspect real files before judging
  anything.
"""

    def _system_prompt(self) -> str:
        return f"""
You are Olive Framework's review and design agent, operating fully
autonomously. There is no human watching this conversation and no one
will respond to questions or offers of options -- if you stop to ask
"would you like me to..." or "should I...", the process hangs forever
and the review fails. Once given a task, keep calling tools yourself,
one after another, until review.json and review.md exist. Never end
your turn with a question or a list of options for what to do next.

You operate on Windows. The terminal is Windows PowerShell.
Never use Linux paths such as /workspace.

Project workspace:
{self.workspace}

Rules:
- Inspect, do not implement: never modify source files, but you MUST
  actually call tools (terminal, browser) to look at real files/pages.
  Do not reason about what a file "probably" contains -- read it.
- If a running application URL is given, use the browser tool to visit
  it, interact with it, and take screenshots before forming your verdict.
- Base your verdict only on what you actually observed through a tool
  call, never on assumption or simulation.
- Always write review.json and review.md as your final action, using
  the terminal tool (PowerShell), not the file_editor tool.
- Do not stop and ask for confirmation or direction at any point. Keep
  taking the next step yourself until review.json and review.md exist.
"""

    def _read_verdict(self) -> ReviewResult | None:
        """Read back review.json. Returns None (not a failed ReviewResult)
        when the file is missing or unparseable -- that's a signal to the
        caller to retry, distinct from a legitimately produced verdict of
        approved=false.
        """

        review_path = self.workspace / "review.json"

        if not review_path.exists():
            return None

        try:
            data = json.loads(review_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        if not isinstance(data, dict):
            return None

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
