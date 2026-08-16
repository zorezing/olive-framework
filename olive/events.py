from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class EventType(str, Enum):
    """The structured event vocabulary described in the project spec."""

    PROJECT_LOADED = "PROJECT_LOADED"
    PLANNER_STARTED = "PLANNER_STARTED"
    PLAN_CREATED = "PLAN_CREATED"
    TASK_CREATED = "TASK_CREATED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_SKIPPED = "TASK_SKIPPED"
    FILE_CREATED = "FILE_CREATED"
    FILE_MODIFIED = "FILE_MODIFIED"
    COMMAND_STARTED = "COMMAND_STARTED"
    COMMAND_FINISHED = "COMMAND_FINISHED"
    TEST_STARTED = "TEST_STARTED"
    TEST_PASSED = "TEST_PASSED"
    TEST_FAILED = "TEST_FAILED"
    APPLICATION_STARTED = "APPLICATION_STARTED"
    BROWSER_OPENED = "BROWSER_OPENED"
    SCREENSHOT_CAPTURED = "SCREENSHOT_CAPTURED"
    RESEARCH_STARTED = "RESEARCH_STARTED"
    RESEARCH_FOUND = "RESEARCH_FOUND"
    REVIEW_STARTED = "REVIEW_STARTED"
    REVIEW_CREATED = "REVIEW_CREATED"
    FIX_REQUESTED = "FIX_REQUESTED"
    CI_STARTED = "CI_STARTED"
    CI_PASSED = "CI_PASSED"
    CI_FAILED = "CI_FAILED"
    ORCHESTRATION_COMPLETED = "ORCHESTRATION_COMPLETED"
    PROJECT_COMPLETED = "PROJECT_COMPLETED"


@dataclass(frozen=True)
class Event:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }


class EventBus:
    """In-process publish/subscribe event bus.

    Every published event is retained in ``log`` regardless of whether
    anything is subscribed, so a bus created purely to collect history
    (e.g. for later persistence) doesn't need a subscriber.
    """

    def __init__(self) -> None:
        self._subscribers: list[Callable[[Event], None]] = []
        self._log: list[Event] = []

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        self._subscribers.append(handler)

    def publish(self, event_type: EventType, **payload: Any) -> Event:
        event = Event(type=event_type, payload=payload)
        self._log.append(event)

        for handler in self._subscribers:
            handler(event)

        return event

    @property
    def log(self) -> list[Event]:
        return list(self._log)
