import json

from olive.events import EventBus, EventType
from olive.persistence import StateStore


def test_completed_task_ids_empty_for_fresh_store(tmp_path):
    store = StateStore(tmp_path / "state")

    assert store.completed_task_ids() == set()


def test_task_completed_event_recorded_as_completed(tmp_path):
    store = StateStore(tmp_path / "state")
    bus = EventBus()
    store.attach(bus)

    bus.publish(EventType.TASK_STARTED, task_id="TASK-001")
    bus.publish(EventType.TASK_COMPLETED, task_id="TASK-001", message="done")

    assert store.completed_task_ids() == {"TASK-001"}


def test_task_failed_event_not_recorded_as_completed(tmp_path):
    store = StateStore(tmp_path / "state")
    bus = EventBus()
    store.attach(bus)

    bus.publish(EventType.TASK_STARTED, task_id="TASK-001")
    bus.publish(EventType.TASK_FAILED, task_id="TASK-001", message="boom")

    assert store.completed_task_ids() == set()


def test_events_are_streamed_to_disk_as_jsonl(tmp_path):
    store = StateStore(tmp_path / "state")
    bus = EventBus()
    store.attach(bus)

    bus.publish(EventType.PROJECT_LOADED, name="Demo")
    bus.publish(EventType.TASK_STARTED, task_id="TASK-001")

    lines = store.events_path.read_text(encoding="utf-8").strip().splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0])["type"] == "PROJECT_LOADED"
    assert json.loads(lines[1])["type"] == "TASK_STARTED"


def test_state_survives_reload_from_same_directory(tmp_path):
    state_dir = tmp_path / "state"

    first_store = StateStore(state_dir)
    bus = EventBus()
    first_store.attach(bus)

    bus.publish(EventType.TASK_STARTED, task_id="TASK-001")
    bus.publish(EventType.TASK_COMPLETED, task_id="TASK-001", message="done")

    second_store = StateStore(state_dir)

    assert second_store.completed_task_ids() == {"TASK-001"}


def test_events_append_across_reloads(tmp_path):
    state_dir = tmp_path / "state"

    first_store = StateStore(state_dir)
    bus1 = EventBus()
    first_store.attach(bus1)
    bus1.publish(EventType.TASK_STARTED, task_id="TASK-001")

    second_store = StateStore(state_dir)
    bus2 = EventBus()
    second_store.attach(bus2)
    bus2.publish(EventType.TASK_COMPLETED, task_id="TASK-001", message="done")

    lines = second_store.events_path.read_text(encoding="utf-8").strip().splitlines()

    assert len(lines) == 2
