import json
from pathlib import Path

from olive.events import Event, EventBus, EventType
from olive.state.task_state import TaskStatus


class StateStore:
    """Persists task status and the full event log to disk as a run
    progresses, so an interrupted orchestration can be resumed.

    Every event is appended to ``events.jsonl`` as it's published (not
    just dumped at the end), and ``task_state.json`` is rewritten after
    every task status change. A later run pointed at the same directory
    can read back which tasks already completed and skip them.
    """

    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / "task_state.json"
        self.events_path = self.state_dir / "events.jsonl"
        self._statuses: dict[str, str] = {}

        if self.state_path.exists():
            self._statuses = json.loads(
                self.state_path.read_text(encoding="utf-8")
            )

    def attach(self, events: EventBus) -> None:
        events.subscribe(self._on_event)

    def _on_event(self, event: Event) -> None:
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict()) + "\n")

        task_id = event.payload.get("task_id")

        if not task_id:
            return

        if event.type == EventType.TASK_STARTED:
            self._statuses[task_id] = TaskStatus.RUNNING.value
        elif event.type == EventType.TASK_COMPLETED:
            self._statuses[task_id] = TaskStatus.COMPLETED.value
        elif event.type == EventType.TASK_FAILED:
            self._statuses[task_id] = TaskStatus.FAILED.value
        else:
            return

        self.state_path.write_text(
            json.dumps(self._statuses, indent=2), encoding="utf-8"
        )

    def completed_task_ids(self) -> set[str]:
        return {
            task_id
            for task_id, status in self._statuses.items()
            if status == TaskStatus.COMPLETED.value
        }
