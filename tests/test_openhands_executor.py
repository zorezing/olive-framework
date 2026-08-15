from pathlib import Path

import pytest

pytest.importorskip("openhands", reason="requires the openhands optional dependency")

from olive.state.task import Task
from olive.state.task_state import TaskStatus
from olive.workflow.openhands_executor import OpenHandsExecutor


WORKSPACE = Path(__file__).resolve().parents[1]


def test_openhands_executor_creates_file():
    target = WORKSPACE / "OPENHANDS_EXECUTOR_TEST.txt"

    if target.exists():
        target.unlink()

    executor = OpenHandsExecutor(
        workspace=WORKSPACE,
        model="qwen3:8b",
    )

    task = Task(
        id="OPENHANDS-TEST-001",
        title="Create OpenHands executor test file",
        description=(
            "Create OPENHANDS_EXECUTOR_TEST.txt in the current workspace. "
            "Put exactly this text inside it: "
            "Olive Framework OpenHands executor works. "
            "Use the terminal tool to actually create the file."
        ),
        task_type="testing",
    )

    result = executor.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert target.exists()
    assert target.read_text(encoding="utf-8-sig").strip() == (
        "Olive Framework OpenHands executor works."
    )

    target.unlink()
