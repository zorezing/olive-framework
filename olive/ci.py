import subprocess
from dataclasses import dataclass
from pathlib import Path

from olive.events import EventBus, EventType


@dataclass
class CIResult:
    command: str
    passed: bool
    exit_code: int
    output: str


class CIRunner:
    """Runs a fixed sequence of shell commands in the workspace as a
    completion gate.

    Olive doesn't know or guess what stack the generated project uses, so
    the commands (test runner, build, health check, ...) are supplied
    explicitly rather than inferred. Commands run in order and stop at the
    first failure, like a typical CI pipeline.
    """

    def __init__(
        self,
        workspace: Path,
        commands: list[str],
        events: EventBus | None = None,
        timeout: int = 600,
    ):
        self.workspace = Path(workspace)
        self.commands = list(commands)
        self.events = events or EventBus()
        self.timeout = timeout

    def run(self) -> list[CIResult]:
        results: list[CIResult] = []

        for command in self.commands:
            self.events.publish(EventType.CI_STARTED, command=command)

            try:
                completed = subprocess.run(
                    command,
                    cwd=self.workspace,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                passed = completed.returncode == 0
                exit_code = completed.returncode
                output = completed.stdout + completed.stderr
            except subprocess.TimeoutExpired:
                passed = False
                exit_code = -1
                output = f"Command timed out after {self.timeout}s"

            results.append(
                CIResult(
                    command=command,
                    passed=passed,
                    exit_code=exit_code,
                    output=output,
                )
            )

            self.events.publish(
                EventType.CI_PASSED if passed else EventType.CI_FAILED,
                command=command,
                exit_code=exit_code,
            )

            if not passed:
                break

        return results

    @staticmethod
    def all_passed(results: list[CIResult]) -> bool:
        return all(result.passed for result in results)
