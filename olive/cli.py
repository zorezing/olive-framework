import argparse
import contextlib
import json
from pathlib import Path

from olive.events import EventBus, EventType
from olive.state.parser import ProjectParser
from olive.orchestrator.engine import Orchestrator
from olive.workflow.fake_executor import FakeExecutor
from olive.workflow.mock_planner import MockPlanner


def build_planner(name: str, ollama_url: str, model: str):
    if name == "mock":
        return MockPlanner()

    if name == "deepseek":
        from olive.workflow.deepseek_planner import DeepSeekPlanner
        from olive.workflow.ollama_client import OllamaClient

        return DeepSeekPlanner(
            client=OllamaClient(base_url=ollama_url),
            model=model,
        )

    raise ValueError(f"Unknown planner: {name}")


def build_executor(name: str, workspace: Path, ollama_url: str, model: str):
    if name == "fake":
        return FakeExecutor()

    if name == "openhands":
        from olive.workflow.openhands_executor import OpenHandsExecutor

        return OpenHandsExecutor(
            workspace=workspace,
            model=model,
            ollama_base_url=ollama_url,
        )

    raise ValueError(f"Unknown executor: {name}")


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
        default="deepseek-r1:8b",
        help="Ollama model used by the deepseek planner",
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

    args = parser.parse_args(argv)

    events = EventBus()
    ui = None

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
        planner = build_planner(args.planner, args.ollama_url, args.planner_model)
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
            executor = build_executor(
                args.executor, workspace, args.ollama_url, args.coder_model
            )
            if ui is not None:
                ui.executor_name = args.executor

            orchestrator = Orchestrator(graph=graph, executor=executor, events=events)
            orchestrator.run()

            if orchestrator.is_complete():
                status("\nAll tasks completed.")
            else:
                status("\nOrchestration finished with incomplete tasks.")
                exit_code = 1

        if args.events_log:
            with args.events_log.open("w", encoding="utf-8") as handle:
                for event in events.log:
                    handle.write(json.dumps(event.to_dict()) + "\n")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
