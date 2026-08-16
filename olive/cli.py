import argparse
import contextlib
import json
from pathlib import Path

from olive.events import EventBus, EventType
from olive.state.parser import ProjectParser
from olive.orchestrator.engine import Orchestrator
from olive.workflow.fake_executor import FakeExecutor
from olive.workflow.mock_planner import MockPlanner


def build_planner(name: str, ollama_url: str, model: str, ollama_timeout: int):
    if name == "mock":
        return MockPlanner()

    if name == "deepseek":
        from olive.workflow.deepseek_planner import DeepSeekPlanner
        from olive.workflow.ollama_client import OllamaClient

        return DeepSeekPlanner(
            client=OllamaClient(base_url=ollama_url, timeout=ollama_timeout),
            model=model,
        )

    raise ValueError(f"Unknown planner: {name}")


def build_executor(
    name: str,
    workspace: Path,
    ollama_url: str,
    model: str,
    persistence_dir: Path | None = None,
):
    if name == "fake":
        return FakeExecutor()

    if name == "openhands":
        from olive.workflow.openhands_executor import OpenHandsExecutor

        return OpenHandsExecutor(
            workspace=workspace,
            model=model,
            ollama_base_url=ollama_url,
            persistence_dir=persistence_dir,
        )

    raise ValueError(f"Unknown executor: {name}")


def build_reviewer(
    name: str,
    workspace: Path,
    ollama_url: str,
    model: str,
    review_url: str | None,
    ollama_timeout: int,
    persistence_dir: Path | None = None,
):
    if name == "none":
        return None

    if name == "mock":
        from olive.workflow.mock_reviewer import MockReviewer

        return MockReviewer()

    if name == "ollama":
        from olive.workflow.ollama_client import OllamaClient
        from olive.workflow.simple_reviewer import SimpleReviewer

        return SimpleReviewer(
            workspace=workspace,
            client=OllamaClient(base_url=ollama_url, timeout=ollama_timeout),
            model=model,
        )

    if name == "openhands":
        from olive.workflow.openhands_reviewer import OpenHandsReviewer

        return OpenHandsReviewer(
            workspace=workspace,
            model=model,
            ollama_base_url=ollama_url,
            review_url=review_url,
            persistence_dir=persistence_dir,
        )

    raise ValueError(f"Unknown reviewer: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="olive",
        description=(
            "Parse a PROJECT.md, plan it into a task graph, and "
            "execute the resulting tasks."
        ),
    )
    parser.add_argument(
        "project",
        type=Path,
        help="Path to a PROJECT.md file",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Execution workspace (default: PROJECT.md's parent directory)",
    )
    parser.add_argument(
        "--planner",
        choices=["mock", "deepseek"],
        default="mock",
        help="Planning agent to use (default: mock)",
    )
    parser.add_argument(
        "--executor",
        choices=["fake", "openhands"],
        default="fake",
        help="Execution agent to use (default: fake)",
    )
    parser.add_argument(
        "--planner-model",
        default="qwen3:8b",
        help=(
            "Ollama model used by the deepseek planner (default: qwen3:8b "
            "-- live-tested faster and more reliable than deepseek-r1:8b "
            "on modest hardware; see README/DeepSeekPlanner docstring). "
            "Pass deepseek-r1:8b explicitly to use the model the project "
            "spec originally envisioned for this role."
        ),
    )
    parser.add_argument(
        "--coder-model",
        default="qwen3:8b",
        help="Ollama model used by the openhands executor",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Base URL of the local Ollama server",
    )
    parser.add_argument(
        "--ollama-timeout",
        type=int,
        default=900,
        help=(
            "Per-request timeout in seconds for the deepseek planner's "
            "Ollama calls (default: 900)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the project but do not execute any tasks",
    )
    parser.add_argument(
        "--events-log",
        type=Path,
        default=None,
        help="Write the full event log as JSON lines to this path",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Show a live terminal dashboard instead of plain log output",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help=(
            "Persist task state and the event log to this directory as "
            "the run progresses, enabling --resume later"
        ),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip tasks already marked completed in --state-dir",
    )
    parser.add_argument(
        "--ci-command",
        action="append",
        default=[],
        metavar="CMD",
        help=(
            "Shell command to run in the workspace as a completion gate "
            "after all tasks finish (repeatable; stops at first failure)"
        ),
    )
    parser.add_argument(
        "--ci-timeout",
        type=int,
        default=600,
        help="Per-command timeout in seconds for --ci-command (default: 600)",
    )
    parser.add_argument(
        "--reviewer",
        choices=["none", "mock", "ollama", "openhands"],
        default="none",
        help=(
            "Reviewer agent to run once tasks and CI pass (default: none, "
            "i.e. skip review). 'ollama' reads workspace files itself and "
            "asks a single Ollama chat completion for a verdict -- no "
            "agentic tool use, live-verified reliable. 'openhands' runs a "
            "real agent with browser tool access; only actually needed "
            "for --review-url (live-tested unreliable for source-only "
            "review with qwen3:8b -- see README). Prefer 'ollama' unless "
            "you're passing --review-url."
        ),
    )
    parser.add_argument(
        "--review-model",
        default="qwen3:8b",
        help=(
            "Ollama model used by the reviewer (default: qwen3:8b -- the "
            "only model verified reliable for this project's local-model "
            "roles so far; see README)"
        ),
    )
    parser.add_argument(
        "--review-url",
        default=None,
        help=(
            "URL of a running instance of the generated application, for "
            "the openhands reviewer to visit with its browser tool "
            "(requires --reviewer openhands; 'ollama' cannot browse)"
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=0,
        help="Retry a failing task up to this many times before giving up (default: 0)",
    )

    args = parser.parse_args(argv)

    if args.resume and not args.state_dir:
        parser.error("--resume requires --state-dir")

    if args.review_url and args.reviewer != "openhands":
        parser.error("--review-url requires --reviewer openhands")

    needs_ollama = (
        args.planner == "deepseek"
        or (not args.dry_run and args.executor == "openhands")
        or (not args.dry_run and args.reviewer in ("ollama", "openhands"))
    )

    if needs_ollama:
        from olive.workflow.ollama_client import OllamaClient

        if not OllamaClient(base_url=args.ollama_url).is_available():
            parser.error(
                f"Ollama is not reachable at {args.ollama_url}. Start Ollama "
                "and make sure the required models are pulled before using "
                "--planner deepseek, --executor openhands, or "
                "--reviewer openhands."
            )

    try:
        return _execute(args)
    except KeyboardInterrupt:
        message = "\nInterrupted."
        if args.state_dir:
            message += (
                f" Progress saved to {args.state_dir} -- resume with --resume."
            )
        print(message)
        return 130


def _execute(args: argparse.Namespace) -> int:
    events = EventBus()
    ui = None
    state_store = None

    if args.state_dir:
        from olive.persistence import StateStore

        state_store = StateStore(args.state_dir)
        state_store.attach(events)

    if args.ui:
        from olive.ui import LiveConsoleUI

        ui = LiveConsoleUI()
        ui.attach(events)

    def status(message: str) -> None:
        if ui is None:
            print(message)

    with ui if ui is not None else contextlib.nullcontext():
        project = ProjectParser().parse(args.project)
        events.publish(EventType.PROJECT_LOADED, name=project.name, goal=project.goal)

        status(f"Project: {project.name}")
        status(f"Goal: {project.goal}")

        events.publish(EventType.PLANNER_STARTED, planner=args.planner)
        planner = build_planner(
            args.planner, args.ollama_url, args.planner_model, args.ollama_timeout
        )
        graph = planner.create_plan(project)
        graph.validate()

        for task in graph.tasks:
            events.publish(
                EventType.TASK_CREATED,
                task_id=task.id,
                title=task.title,
                dependencies=task.dependencies,
            )
        events.publish(EventType.PLAN_CREATED, task_count=len(graph.tasks))

        status(f"\nPlanned {len(graph.tasks)} task(s):")
        for task in graph.tasks:
            deps = (
                f" (depends on {', '.join(task.dependencies)})"
                if task.dependencies
                else ""
            )
            status(f"  {task.id}: {task.title}{deps}")

        exit_code = 0

        if not args.dry_run:
            workspace = args.workspace or args.project.resolve().parent
            persistence_dir = (
                args.state_dir / "openhands" if args.state_dir else None
            )
            executor = build_executor(
                args.executor,
                workspace,
                args.ollama_url,
                args.coder_model,
                persistence_dir=persistence_dir,
            )
            if ui is not None:
                ui.executor_name = args.executor

            already_completed = (
                state_store.completed_task_ids()
                if args.resume and state_store is not None
                else set()
            )

            orchestrator = Orchestrator(
                graph=graph,
                executor=executor,
                events=events,
                completed=already_completed,
                max_retries=args.max_retries,
            )
            orchestrator.run()

            if orchestrator.is_complete():
                status("\nAll tasks completed.")
                gate_passed = True

                if args.ci_command:
                    from olive.ci import CIRunner

                    status(f"\nRunning {len(args.ci_command)} CI command(s)...")
                    runner = CIRunner(
                        workspace=workspace,
                        commands=args.ci_command,
                        events=events,
                        timeout=args.ci_timeout,
                    )
                    ci_results = runner.run()

                    for result in ci_results:
                        outcome = "PASSED" if result.passed else "FAILED"
                        status(f"  [{outcome}] {result.command}")

                    gate_passed = CIRunner.all_passed(ci_results)
                    status("\nCI passed." if gate_passed else "\nCI failed.")

                if gate_passed and args.reviewer != "none":
                    review_persistence_dir = (
                        args.state_dir / "review" if args.state_dir else None
                    )
                    reviewer = build_reviewer(
                        args.reviewer,
                        workspace,
                        args.ollama_url,
                        args.review_model,
                        args.review_url,
                        args.ollama_timeout,
                        persistence_dir=review_persistence_dir,
                    )

                    status("\nRunning reviewer...")
                    events.publish(EventType.REVIEW_STARTED, reviewer=args.reviewer)
                    review_result = reviewer.review(project)
                    events.publish(
                        EventType.REVIEW_CREATED,
                        approved=review_result.approved,
                        finding_count=len(review_result.findings),
                    )

                    for finding in review_result.findings:
                        status(
                            f"  [{'BLOCKING' if finding.blocking else 'note'}] "
                            f"{finding.summary}"
                        )
                        if finding.blocking:
                            events.publish(
                                EventType.FIX_REQUESTED, summary=finding.summary
                            )

                    gate_passed = review_result.approved
                    status(
                        "\nReview approved."
                        if gate_passed
                        else "\nReview found blocking issues."
                    )

                if gate_passed:
                    events.publish(EventType.PROJECT_COMPLETED)
                else:
                    exit_code = 1
            else:
                from olive.state.task_state import TaskStatus

                blocked = [
                    task_id
                    for task_id, task_status in orchestrator.statuses.items()
                    if task_status == TaskStatus.PENDING
                ]
                status(
                    f"\nOrchestration finished with failures: "
                    f"{sorted(orchestrator.failed)}"
                )
                if blocked:
                    status(f"Blocked (never attempted): {sorted(blocked)}")
                exit_code = 1

        if args.events_log:
            with args.events_log.open("w", encoding="utf-8") as handle:
                for event in events.log:
                    handle.write(json.dumps(event.to_dict()) + "\n")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
