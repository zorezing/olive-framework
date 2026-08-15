from pathlib import Path

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

    executor.execute(
        """
        Create OPENHANDS_EXECUTOR_TEST.txt in the current workspace.
        Put exactly this text inside it:

        Olive Framework OpenHands executor works.

        Use the terminal tool to actually create the file.
        """
    )

    assert target.exists()
    assert target.read_text(encoding="utf-16").strip() == (
        "Olive Framework OpenHands executor works."
    )

    target.unlink()
