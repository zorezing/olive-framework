from olive.events import Event, EventBus, EventType


def test_publish_appends_to_log():
    bus = EventBus()

    bus.publish(EventType.TASK_STARTED, task_id="TASK-001")

    assert len(bus.log) == 1
    assert bus.log[0].type == EventType.TASK_STARTED
    assert bus.log[0].payload == {"task_id": "TASK-001"}


def test_publish_returns_the_event():
    bus = EventBus()

    event = bus.publish(EventType.PROJECT_LOADED, name="Demo")

    assert isinstance(event, Event)
    assert event.type == EventType.PROJECT_LOADED
    assert event.payload["name"] == "Demo"


def test_log_preserves_publish_order():
    bus = EventBus()

    bus.publish(EventType.TASK_STARTED, task_id="TASK-001")
    bus.publish(EventType.TASK_COMPLETED, task_id="TASK-001")
    bus.publish(EventType.TASK_STARTED, task_id="TASK-002")

    assert [event.type for event in bus.log] == [
        EventType.TASK_STARTED,
        EventType.TASK_COMPLETED,
        EventType.TASK_STARTED,
    ]


def test_log_is_a_copy():
    bus = EventBus()

    bus.publish(EventType.TASK_STARTED, task_id="TASK-001")
    snapshot = bus.log
    bus.publish(EventType.TASK_COMPLETED, task_id="TASK-001")

    assert len(snapshot) == 1
    assert len(bus.log) == 2


def test_subscribers_receive_every_event_in_order():
    bus = EventBus()
    received = []

    bus.subscribe(received.append)

    bus.publish(EventType.TASK_STARTED, task_id="TASK-001")
    bus.publish(EventType.TASK_COMPLETED, task_id="TASK-001")

    assert [event.type for event in received] == [
        EventType.TASK_STARTED,
        EventType.TASK_COMPLETED,
    ]


def test_multiple_subscribers_all_receive_events():
    bus = EventBus()
    first, second = [], []

    bus.subscribe(first.append)
    bus.subscribe(second.append)

    bus.publish(EventType.TASK_STARTED, task_id="TASK-001")

    assert len(first) == 1
    assert len(second) == 1


def test_event_to_dict_is_json_serializable():
    import json

    bus = EventBus()

    event = bus.publish(EventType.TASK_STARTED, task_id="TASK-001")

    serialized = json.dumps(event.to_dict())
    restored = json.loads(serialized)

    assert restored["type"] == "TASK_STARTED"
    assert restored["payload"] == {"task_id": "TASK-001"}
    assert "timestamp" in restored
