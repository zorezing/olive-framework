import time
from pathlib import Path

from olive.state.task import Task
from olive.workflow.openhands_executor import OpenHandsExecutor


workspace = Path(__file__).resolve().parents[1]

task = Task(
    id="PROFILE-001",
    title="Create profiling file",
    description=(
        "Create PROFILE_TEST.txt in the project workspace with "
        "the exact text: Olive Framework profiling works."
    ),
    task_type="testing",
)

start = time.perf_counter()

executor_start = time.perf_counter()
executor = OpenHandsExecutor(
    workspace=workspace,
    model="qwen3:8b",
)
executor_end = time.perf_counter()

result_start = time.perf_counter()
result = executor.execute(task)
result_end = time.perf_counter()

total_end = time.perf_counter()

print(f"executor initialization: {executor_end - executor_start:.2f}s")
print(f"task execution:         {result_end - result_start:.2f}s")
print(f"total:                  {total_end - start:.2f}s")
print(f"status:                 {result.status}")

target = workspace / "PROFILE_TEST.txt"
if target.exists():
    target.unlink()
