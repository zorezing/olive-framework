from olive.events import EventBus, EventType
from olive.ui import DashboardState, LiveConsoleUI, render


def test_project_loaded_sets_project_name():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.PROJECT_LOADED, name="Demo")

    assert state.project_name == "Demo"


def test_project_loaded_sets_goal():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.PROJECT_LOADED, name="Demo", goal="Build something.")

    assert state.goal == "Build something."


def test_planner_started_sets_planning_flag():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.PLANNER_STARTED, planner="mock")

    assert state.planning is True
    assert state.planner_name == "mock"


def test_task_created_adds_task_with_pending_status():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(
        EventType.TASK_CREATED,
        task_id="TASK-001",
        title="Initialize",
        dependencies=[],
    )

    assert "TASK-001" in state.tasks
    assert state.tasks["TASK-001"].status == "pending"
    assert state.tasks["TASK-001"].title == "Initialize"


def test_plan_created_clears_planning_flag():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.PLANNER_STARTED, planner="mock")
    bus.publish(EventType.PLAN_CREATED, task_count=1)

    assert state.planning is False


def test_task_started_marks_running_and_current():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.TASK_CREATED, task_id="TASK-001", title="X", dependencies=[])
    bus.publish(EventType.TASK_STARTED, task_id="TASK-001", title="X")

    assert state.tasks["TASK-001"].status == "running"
    assert state.current_task_id == "TASK-001"


def test_task_completed_clears_current_and_marks_completed():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.TASK_CREATED, task_id="TASK-001", title="X", dependencies=[])
    bus.publish(EventType.TASK_STARTED, task_id="TASK-001", title="X")
    bus.publish(EventType.TASK_COMPLETED, task_id="TASK-001", message="done")

    assert state.tasks["TASK-001"].status == "completed"
    assert state.current_task_id is None


def test_task_failed_marks_failed_and_clears_current():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.TASK_CREATED, task_id="TASK-001", title="X", dependencies=[])
    bus.publish(EventType.TASK_STARTED, task_id="TASK-001", title="X")
    bus.publish(EventType.TASK_FAILED, task_id="TASK-001", message="boom")

    assert state.tasks["TASK-001"].status == "failed"
    assert state.current_task_id is None


def test_orchestration_completed_sets_flag():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.ORCHESTRATION_COMPLETED)

    assert state.orchestration_complete is True


def test_recent_log_respects_count():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)
    for i in range(20):
        bus.publish(EventType.TASK_STARTED, task_id=f"TASK-{i:03}")

    assert len(state.recent_log(5)) == 5
    assert len(state.log) == 20


def test_render_does_not_raise_on_empty_state():
    state = DashboardState()

    renderable = render(state)

    assert renderable is not None


def test_render_does_not_raise_with_populated_state():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.PROJECT_LOADED, name="Demo")
    bus.publish(EventType.PLANNER_STARTED, planner="mock")
    bus.publish(EventType.TASK_CREATED, task_id="TASK-001", title="X", dependencies=[])
    bus.publish(EventType.PLAN_CREATED, task_count=1)
    bus.publish(EventType.TASK_STARTED, task_id="TASK-001", title="X")
    bus.publish(EventType.TASK_COMPLETED, task_id="TASK-001", message="done")
    bus.publish(EventType.ORCHESTRATION_COMPLETED)

    renderable = render(state, executor_name="fake")

    assert renderable is not None


def test_live_console_ui_enter_exit_does_not_raise():
    events = EventBus()
    ui = LiveConsoleUI()
    ui.attach(events)

    with ui:
        events.publish(EventType.PROJECT_LOADED, name="Demo")
        events.publish(EventType.TASK_CREATED, task_id="TASK-001", title="X", dependencies=[])

    assert ui.state.project_name == "Demo"
