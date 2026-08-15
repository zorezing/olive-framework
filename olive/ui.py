from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console, ConsoleRenderable, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from olive.events import Event, EventBus, EventType


STATUS_STYLES = {
    "pending": "dim",
    "running": "bold yellow",
    "completed": "bold green",
    "passed": "bold green",
    "failed": "bold red",
}


@dataclass
class TaskProgress:
    id: str
    title: str
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"


@dataclass
class CIStepProgress:
    command: str
    status: str = "running"


@dataclass
class ReviewProgress:
    reviewer: str
    running: bool = True
    approved: bool | None = None
    findings: list[str] = field(default_factory=list)


class DashboardState:
    """Tracks live progress derived from an EventBus's event stream.

    Kept separate from rendering so it can be unit-tested without a real
    terminal attached.
    """

    def __init__(self) -> None:
        self.project_name = ""
        self.goal = ""
        self.planner_name = ""
        self.planning = False
        self.tasks: dict[str, TaskProgress] = {}
        self.current_task_id: str | None = None
        self.orchestration_complete = False
        self.project_complete = False
        self.ci_steps: list[CIStepProgress] = []
        self.review: ReviewProgress | None = None
        self.log: list[Event] = []

    def handle(self, event: Event) -> None:
        self.log.append(event)

        if event.type == EventType.PROJECT_LOADED:
            self.project_name = event.payload.get("name", self.project_name)
            self.goal = event.payload.get("goal", self.goal)

        elif event.type == EventType.PLANNER_STARTED:
            self.planner_name = event.payload.get("planner", "")
            self.planning = True

        elif event.type == EventType.TASK_CREATED:
            task_id = event.payload["task_id"]
            self.tasks[task_id] = TaskProgress(
                id=task_id,
                title=event.payload.get("title", ""),
                dependencies=event.payload.get("dependencies", []),
            )

        elif event.type == EventType.PLAN_CREATED:
            self.planning = False

        elif event.type == EventType.TASK_STARTED:
            task_id = event.payload["task_id"]
            self.current_task_id = task_id
            if task_id in self.tasks:
                self.tasks[task_id].status = "running"

        elif event.type == EventType.TASK_COMPLETED:
            task_id = event.payload["task_id"]
            if task_id in self.tasks:
                self.tasks[task_id].status = "completed"
            if self.current_task_id == task_id:
                self.current_task_id = None

        elif event.type == EventType.TASK_FAILED:
            task_id = event.payload["task_id"]
            if task_id in self.tasks:
                self.tasks[task_id].status = "failed"
            if self.current_task_id == task_id:
                self.current_task_id = None

        elif event.type == EventType.ORCHESTRATION_COMPLETED:
            self.orchestration_complete = True

        elif event.type == EventType.CI_STARTED:
            self.ci_steps.append(
                CIStepProgress(command=event.payload.get("command", ""))
            )

        elif event.type == EventType.CI_PASSED:
            if self.ci_steps:
                self.ci_steps[-1].status = "passed"

        elif event.type == EventType.CI_FAILED:
            if self.ci_steps:
                self.ci_steps[-1].status = "failed"

        elif event.type == EventType.REVIEW_STARTED:
            self.review = ReviewProgress(reviewer=event.payload.get("reviewer", ""))

        elif event.type == EventType.REVIEW_CREATED:
            if self.review is not None:
                self.review.running = False
                self.review.approved = event.payload.get("approved")

        elif event.type == EventType.FIX_REQUESTED:
            if self.review is not None:
                self.review.findings.append(event.payload.get("summary", ""))

        elif event.type == EventType.PROJECT_COMPLETED:
            self.project_complete = True

    def recent_log(self, count: int = 8) -> list[Event]:
        return self.log[-count:]


def render(state: DashboardState, executor_name: str = "") -> ConsoleRenderable:
    header = Text(state.project_name or "(unnamed project)", style="bold cyan")
    if state.goal:
        header.append(f"\n{state.goal}", style="dim")

    tasks_table = Table(box=None, show_header=True, header_style="bold", expand=True)
    tasks_table.add_column("Task")
    tasks_table.add_column("Title")
    tasks_table.add_column("Depends on")
    tasks_table.add_column("Status")

    for task in state.tasks.values():
        tasks_table.add_row(
            task.id,
            task.title,
            ", ".join(task.dependencies) or "-",
            Text(task.status, style=STATUS_STYLES.get(task.status, "white")),
        )

    planner_status = (
        "planning..." if state.planning else f"{len(state.tasks)} task(s) planned"
    )
    planner_panel = Panel(
        tasks_table if state.tasks else Text("(no tasks yet)", style="dim"),
        title=f"Planner: {state.planner_name or 'n/a'} -- {planner_status}",
    )

    if state.current_task_id and state.current_task_id in state.tasks:
        current = state.tasks[state.current_task_id]
        coder_text = Text(
            f"Running {current.id}: {current.title}", style="bold yellow"
        )
    elif state.orchestration_complete:
        coder_text = Text("All tasks completed.", style="bold green")
    else:
        coder_text = Text("Idle", style="dim")

    coder_panel = Panel(coder_text, title=f"Coder: {executor_name or 'n/a'}")

    if state.ci_steps:
        ci_text = Text()
        for step in state.ci_steps:
            ci_text.append(
                step.status.upper().ljust(8),
                style=STATUS_STYLES.get(step.status, "white"),
            )
            ci_text.append(f"{step.command}\n")
    elif state.project_complete:
        ci_text = Text("No CI configured.", style="dim")
    else:
        ci_text = Text("(not run yet)", style="dim")

    ci_panel = Panel(ci_text, title="CI")

    if state.review is None:
        review_text = Text(
            "No reviewer configured." if state.project_complete else "(not run yet)",
            style="dim",
        )
    elif state.review.running:
        review_text = Text(f"Reviewing ({state.review.reviewer})...", style="bold yellow")
    else:
        review_text = Text()
        review_text.append(
            "APPROVED" if state.review.approved else "CHANGES REQUESTED",
            style="bold green" if state.review.approved else "bold red",
        )
        for finding in state.review.findings:
            review_text.append(f"\n- {finding}")

    review_panel = Panel(review_text, title="Reviewer")

    log_lines = Text()
    for event in state.recent_log():
        detail = event.payload.get("task_id") or event.payload.get("name") or ""
        log_lines.append(event.type.value, style="bold")
        if detail:
            log_lines.append(f" ({detail})")
        log_lines.append("\n")

    log_panel = Panel(
        log_lines if state.log else Text("(no events yet)", style="dim"),
        title="Recent events",
    )

    return Group(
        Panel(header, title="Olive Framework"),
        planner_panel,
        coder_panel,
        ci_panel,
        review_panel,
        log_panel,
    )


class LiveConsoleUI:
    """A terminal-only progress dashboard driven entirely by EventBus events."""

    def __init__(self) -> None:
        self.state = DashboardState()
        self.executor_name = ""
        self._console = Console()
        self._live: Live | None = None

    def attach(self, events: EventBus) -> None:
        events.subscribe(self._on_event)

    def _on_event(self, event: Event) -> None:
        self.state.handle(event)
        if self._live is not None:
            self._live.update(render(self.state, self.executor_name), refresh=True)

    def __enter__(self) -> "LiveConsoleUI":
        self._live = Live(
            render(self.state, self.executor_name),
            console=self._console,
            refresh_per_second=4,
            transient=False,
        )
        self._live.__enter__()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._live is not None:
            self._live.__exit__(*exc_info)
            self._live = None
