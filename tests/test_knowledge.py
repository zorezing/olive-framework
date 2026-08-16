import json

from olive.events import EventBus, EventType
from olive.knowledge import KnowledgeStore
from olive.state.review import Finding, ReviewResult


def test_plan_md_written_on_plan_created(tmp_path):
    store = KnowledgeStore(tmp_path)
    bus = EventBus()
    store.attach(bus)

    bus.publish(EventType.PROJECT_LOADED, name="Demo", goal="Build a thing")
    bus.publish(EventType.PLANNER_STARTED, planner="deepseek")
    bus.publish(
        EventType.TASK_CREATED,
        task_id="TASK-001",
        title="Initialize project",
        dependencies=[],
    )
    bus.publish(
        EventType.TASK_CREATED,
        task_id="TASK-002",
        title="Implement feature",
        dependencies=["TASK-001"],
    )
    bus.publish(EventType.PLAN_CREATED, task_count=2)

    content = store.plan_path.read_text(encoding="utf-8")

    assert "# Plan: Demo" in content
    assert "Build a thing" in content
    assert "deepseek" in content
    assert "TASK-001" in content
    assert "TASK-002" in content
    assert "depends on: TASK-001" in content
    assert "depends on: none" in content


def test_plan_md_regenerated_each_time_planning_completes(tmp_path):
    store = KnowledgeStore(tmp_path)
    bus = EventBus()
    store.attach(bus)

    bus.publish(EventType.PROJECT_LOADED, name="Demo", goal="v1")
    bus.publish(EventType.TASK_CREATED, task_id="TASK-001", title="A", dependencies=[])
    bus.publish(EventType.PLAN_CREATED, task_count=1)

    first = store.plan_path.read_text(encoding="utf-8")
    assert "TASK-001" in first

    # A fresh planning pass (e.g. after --resume replans) should replace,
    # not append to, plan.md.
    bus.publish(EventType.TASK_CREATED, task_id="TASK-002", title="B", dependencies=[])
    bus.publish(EventType.PLAN_CREATED, task_count=2)

    second = store.plan_path.read_text(encoding="utf-8")
    assert "TASK-001" in second
    assert "TASK-002" in second
    assert second.count("# Plan:") == 1


def test_record_decision_appends_timestamped_lines(tmp_path):
    store = KnowledgeStore(tmp_path)

    store.record_decision("Using planner=deepseek (model=qwen3:8b)")
    store.record_decision("CI passed")

    content = store.decisions_path.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if line.strip()]

    assert len(lines) == 2
    assert "Using planner=deepseek (model=qwen3:8b)" in lines[0]
    assert "CI passed" in lines[1]


def test_record_review_writes_numbered_snapshots(tmp_path):
    store = KnowledgeStore(tmp_path)

    result = ReviewResult(
        approved=False,
        findings=[Finding(summary="Missing tests", blocking=True)],
        notes="Needs work.",
    )
    store.record_review(result, reviewer_name="ollama")

    md = (store.reviews_dir / "review-001.md").read_text(encoding="utf-8")
    data = json.loads((store.reviews_dir / "review-001.json").read_text(encoding="utf-8"))

    assert "CHANGES REQUESTED" in md
    assert "Missing tests" in md
    assert "BLOCKING" in md
    assert data["approved"] is False
    assert data["reviewer"] == "ollama"
    assert data["findings"][0]["summary"] == "Missing tests"


def test_record_review_numbers_increment_across_calls(tmp_path):
    store = KnowledgeStore(tmp_path)

    store.record_review(ReviewResult(approved=False), reviewer_name="ollama")
    store.record_review(ReviewResult(approved=True), reviewer_name="ollama")

    assert (store.reviews_dir / "review-001.json").exists()
    assert (store.reviews_dir / "review-002.json").exists()

    second = json.loads(
        (store.reviews_dir / "review-002.json").read_text(encoding="utf-8")
    )
    assert second["approved"] is True


def test_approved_review_has_no_findings_section(tmp_path):
    store = KnowledgeStore(tmp_path)

    store.record_review(
        ReviewResult(approved=True, notes="All good."), reviewer_name="ollama"
    )

    md = (store.reviews_dir / "review-001.md").read_text(encoding="utf-8")

    assert "APPROVED" in md
    assert "## Findings" not in md
