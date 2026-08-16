import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from olive.state.parser import ProjectParser


_SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    ".venv312",
    ".olive",
    ".pytest_cache",
}


@dataclass
class ProjectEntry:
    path: Path  # path to PROJECT.md
    name: str
    goal: str
    requirements: list[str]
    constraints: list[str]
    status: str  # "not started" | "in progress" | "completed" | "needs attention"
    state_dir: Path


def discover_projects(root: Path) -> list[ProjectEntry]:
    """Find every PROJECT.md under root, skipping noise directories.
    Files that fail to parse are silently skipped -- not every PROJECT.md
    a user has lying around is necessarily well-formed yet.
    """

    entries = []

    for path in sorted(Path(root).rglob("PROJECT.md")):
        if any(part in _SKIP_DIR_NAMES for part in path.parts):
            continue

        try:
            project = ProjectParser().parse(path)
        except (FileNotFoundError, ValueError):
            continue

        state_dir = path.parent / ".olive"
        entries.append(
            ProjectEntry(
                path=path,
                name=project.name,
                goal=project.goal,
                requirements=project.requirements,
                constraints=project.constraints,
                status=_determine_status(state_dir),
                state_dir=state_dir,
            )
        )

    return entries


def _determine_status(state_dir: Path) -> str:
    task_state_path = state_dir / "task_state.json"

    if not task_state_path.exists():
        return "not started"

    try:
        statuses = json.loads(task_state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "not started"

    if not statuses:
        return "not started"

    values = set(statuses.values())

    if values <= {"completed", "skipped"}:
        return "completed"
    if "failed" in values:
        return "needs attention"

    return "in progress"


_STATUS_STYLES = {
    "not started": "dim",
    "in progress": "bold yellow",
    "needs attention": "bold red",
    "completed": "bold green",
}


def render_project_table(projects: list[ProjectEntry], root: Path) -> Panel:
    table = Table(box=None, show_header=True, header_style="bold", expand=True)
    table.add_column("#", width=3)
    table.add_column("Name")
    table.add_column("Goal")
    table.add_column("Status")

    for i, entry in enumerate(projects, start=1):
        table.add_row(
            str(i),
            entry.name,
            entry.goal[:60] + ("..." if len(entry.goal) > 60 else ""),
            Text(entry.status, style=_STATUS_STYLES.get(entry.status, "white")),
        )

    body = table if projects else Text(f"(no PROJECT.md found under {root})", style="dim")

    return Panel(body, title=f"Olive Framework -- Projects under {root}")


class Launcher:
    """Interactive project browser: list PROJECT.md files under a root
    directory, and start/resume/create projects. A numbered-menu design
    (not a full curses-style TUI) so it stays simple, dependency-light,
    and testable by injecting a canned input_func and a Console writing
    to an in-memory buffer.
    """

    def __init__(
        self,
        projects_root: Path,
        console: Console | None = None,
        input_func: Callable[[str], str] = input,
    ):
        self.projects_root = Path(projects_root)
        self.console = console or Console()
        self.input_func = input_func

    def run(self) -> int:
        while True:
            projects = discover_projects(self.projects_root)
            self.console.print(render_project_table(projects, self.projects_root))
            self.console.print(
                "\n[bold]Commands:[/bold] number to open a project, "
                "[green]n[/green] new project, [red]q[/red] quit"
            )

            choice = self.input_func("> ").strip().lower()

            if choice in ("q", "quit", "exit"):
                return 0

            if choice in ("n", "new"):
                self._create_project()
                continue

            if choice.isdigit() and 1 <= int(choice) <= len(projects):
                self._project_menu(projects[int(choice) - 1])
                continue

            self.console.print("[red]Unrecognized choice.[/red]")

    def _project_menu(self, entry: ProjectEntry) -> None:
        while True:
            self.console.print(
                Panel(
                    self._project_details(entry),
                    title=entry.name,
                )
            )

            has_state = entry.state_dir.exists()
            options = ["[r]un"]
            if has_state:
                options.append("[R]esume")
            options += ["[v]iew knowledge docs", "[b]ack"]
            self.console.print(f"\n[bold]Options:[/bold] {' / '.join(options)}")

            choice = self.input_func("> ").strip().lower()

            if choice in ("b", "back"):
                return

            if choice == "r":
                self._run_project(entry, resume=False)
                entry.status = _determine_status(entry.state_dir)
                continue

            if choice == "resume" and has_state:
                self._run_project(entry, resume=True)
                entry.status = _determine_status(entry.state_dir)
                continue

            if choice == "v":
                self._view_knowledge(entry)
                continue

            self.console.print("[red]Unrecognized choice.[/red]")

    def _project_details(self, entry: ProjectEntry) -> Text:
        text = Text()
        text.append(f"{entry.path}\n", style="dim")
        text.append(f"\nGoal: {entry.goal}\n")
        if entry.requirements:
            text.append("\nRequirements:\n")
            for r in entry.requirements:
                text.append(f"  - {r}\n")
        if entry.constraints:
            text.append("\nConstraints:\n")
            for c in entry.constraints:
                text.append(f"  - {c}\n")
        text.append(f"\nStatus: {entry.status}\n")
        return text

    def _run_project(self, entry: ProjectEntry, resume: bool) -> None:
        planner = self.input_func(
            "Planner [mock/deepseek] (default: deepseek): "
        ).strip() or "deepseek"
        executor = self.input_func(
            "Executor [fake/openhands] (default: openhands): "
        ).strip() or "openhands"
        reviewer = self.input_func(
            "Reviewer [none/mock/ollama/openhands] (default: ollama): "
        ).strip() or "ollama"
        use_ui = (
            self.input_func("Show live dashboard? [Y/n]: ").strip().lower() or "y"
        ) not in ("n", "no")

        argv = [
            str(entry.path),
            "--planner", planner,
            "--executor", executor,
            "--reviewer", reviewer,
            "--state-dir", str(entry.state_dir),
        ]
        if use_ui:
            argv.append("--ui")
        if resume:
            argv.append("--resume")

        from olive.cli import main as cli_main

        self.console.print(f"\n[bold]Starting {entry.name}...[/bold]\n")
        exit_code = cli_main(argv)
        self.console.print(f"\n[bold]Run finished with exit code {exit_code}.[/bold]")
        self.input_func("\nPress Enter to return to the menu...")

    def _view_knowledge(self, entry: ProjectEntry) -> None:
        plan_path = entry.state_dir / "plan.md"
        decisions_path = entry.state_dir / "decisions.md"
        reviews_dir = entry.state_dir / "reviews"

        if plan_path.exists():
            self.console.print(Panel(plan_path.read_text(encoding="utf-8"), title="plan.md"))
        else:
            self.console.print("[dim]No plan.md yet.[/dim]")

        if decisions_path.exists():
            self.console.print(
                Panel(decisions_path.read_text(encoding="utf-8"), title="decisions.md")
            )
        else:
            self.console.print("[dim]No decisions.md yet.[/dim]")

        if reviews_dir.exists():
            review_files = sorted(reviews_dir.glob("review-*.md"))
            if review_files:
                latest = review_files[-1]
                self.console.print(
                    Panel(latest.read_text(encoding="utf-8"), title=latest.name)
                )
        else:
            self.console.print("[dim]No reviews yet.[/dim]")

        self.input_func("\nPress Enter to continue...")

    def _create_project(self) -> None:
        self.console.print("\n[bold]Create a new project[/bold]")

        dir_name = self.input_func(
            "Directory name (created under the projects root): "
        ).strip()
        if not dir_name:
            self.console.print("[red]Cancelled -- no directory name given.[/red]")
            return

        project_dir = self.projects_root / dir_name
        project_dir.mkdir(parents=True, exist_ok=True)
        project_path = project_dir / "PROJECT.md"

        if project_path.exists():
            self.console.print(f"[red]{project_path} already exists.[/red]")
            return

        name = self.input_func("Project name: ").strip() or dir_name
        goal = self.input_func("Goal: ").strip()

        self.console.print("Requirements (one per line, blank line to finish):")
        requirements = self._read_lines()

        self.console.print("Constraints (one per line, blank line to finish):")
        constraints = self._read_lines()

        content = self._render_project_md(name, goal, requirements, constraints)
        project_path.write_text(content, encoding="utf-8")

        self.console.print(f"\n[bold green]Created {project_path}[/bold green]")
        self.input_func("\nPress Enter to continue...")

    def _read_lines(self) -> list[str]:
        lines = []
        while True:
            line = self.input_func("  - ").strip()
            if not line:
                break
            lines.append(line)
        return lines

    @staticmethod
    def _render_project_md(
        name: str, goal: str, requirements: list[str], constraints: list[str]
    ) -> str:
        lines = [f"# {name}", "", "## Goal", "", goal, "", "## Requirements", ""]
        lines += [f"- {r}" for r in requirements]
        lines += ["", "## Constraints", ""]
        lines += [f"- {c}" for c in constraints]
        lines.append("")
        return "\n".join(lines)


def run_launcher(
    projects_root: Path,
    console: Console | None = None,
    input_func: Callable[[str], str] = input,
) -> int:
    return Launcher(projects_root, console=console, input_func=input_func).run()
