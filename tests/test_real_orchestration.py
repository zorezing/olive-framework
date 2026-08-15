from pathlib import Path

import pytest

pytest.importorskip("openhands", reason="requires the openhands optional dependency")

from olive.orchestrator.engine import Orchestrator
from olive.state.task import Task
from olive.state.task_graph import TaskGraph
from olive.state.task_state import TaskStatus
from olive.workflow.openhands_executor import OpenHandsExecutor


WORKSPACE = Path(__file__).resolve().parents[1]


def test_real_orchestrator_with_openhands():
    target = WORKSPACE / "OLIVE_REAL_TASK_TEST.txt"

    if target.exists():
        target.unlink()

    graph = TaskGraph(
        tasks=[
            Task(
                id="TASK-001",
                title="Create Olive Framework test file",
                description=(
                    "Create OLIVE_REAL_TASK_TEST.txt in the project "
                    "workspace. Put exactly this text inside it: "
                    "Olive Framework real orchestration works."
                ),
                task_type="testing",
            )
        ]
    )

    executor = OpenHandsExecutor(
        workspace=WORKSPACE,
        model="qwen3:8b",
    )

    orchestrator = Orchestrator(
        graph=graph,
        executor=executor,
    )

    orchestrator.run()

    assert orchestrator.is_complete()
    assert orchestrator.statuses["TASK-001"] == TaskStatus.COMPLETED
    assert target.exists()

    content = target.read_text(encoding="utf-8").strip()

    assert content == "Olive Framework real orchestration works."

    target.unlink()
