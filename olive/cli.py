import argparse
from pathlib import Path

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

    args = parser.parse_args(argv)

    project = ProjectParser().parse(args.project)

    print(f"Project: {project.name}")
    print(f"Goal: {project.goal}")

    planner = build_planner(args.planner, args.ollama_url, args.planner_model)
    graph = planner.create_plan(project)
    graph.validate()

    print(f"\nPlanned {len(graph.tasks)} task(s):")
    for task in graph.tasks:
        deps = (
            f" (depends on {', '.join(task.dependencies)})"
            if task.dependencies
            else ""
        )
        print(f"  {task.id}: {task.title}{deps}")

    if args.dry_run:
        return 0

    workspace = args.workspace or args.project.resolve().parent
    executor = build_executor(
        args.executor, workspace, args.ollama_url, args.coder_model
    )

    orchestrator = Orchestrator(graph=graph, executor=executor)
    orchestrator.run()

    if orchestrator.is_complete():
        print("\nAll tasks completed.")
        return 0

    print("\nOrchestration finished with incomplete tasks.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
