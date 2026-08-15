from olive.events import EventBus, EventType
from olive.ui import DashboardState, render


def test_review_started_sets_running_state():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.REVIEW_STARTED, reviewer="openhands")

    assert state.review is not None
    assert state.review.running is True
    assert state.review.reviewer == "openhands"


def test_review_created_sets_approved_and_clears_running():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.REVIEW_STARTED, reviewer="openhands")
    bus.publish(EventType.REVIEW_CREATED, approved=True, finding_count=0)

    assert state.review.running is False
    assert state.review.approved is True


def test_fix_requested_adds_finding():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.REVIEW_STARTED, reviewer="openhands")
    bus.publish(EventType.FIX_REQUESTED, summary="Missing auth check")
    bus.publish(EventType.REVIEW_CREATED, approved=False, finding_count=1)

    assert state.review.approved is False
    assert state.review.findings == ["Missing auth check"]


def test_render_with_review_state_does_not_raise():
    state = DashboardState()
    bus = EventBus()
    bus.subscribe(state.handle)

    bus.publish(EventType.PROJECT_LOADED, name="Demo")
    bus.publish(EventType.REVIEW_STARTED, reviewer="mock")
    bus.publish(EventType.FIX_REQUESTED, summary="Something is off")
    bus.publish(EventType.REVIEW_CREATED, approved=False, finding_count=1)

    renderable = render(state, executor_name="fake")

    assert renderable is not None
