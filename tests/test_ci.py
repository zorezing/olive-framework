import sys

from olive.ci import CIRunner
from olive.events import EventBus, EventType


PY = sys.executable


def test_single_passing_command(tmp_path):
    runner = CIRunner(
        workspace=tmp_path,
        commands=[f'"{PY}" -c "print(1)"'],
    )

    results = runner.run()

    assert len(results) == 1
    assert results[0].passed is True
    assert results[0].exit_code == 0
    assert CIRunner.all_passed(results) is True


def test_single_failing_command(tmp_path):
    runner = CIRunner(
        workspace=tmp_path,
        commands=[f'"{PY}" -c "import sys; sys.exit(1)"'],
    )

    results = runner.run()

    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].exit_code == 1
    assert CIRunner.all_passed(results) is False


def test_stops_at_first_failure(tmp_path):
    runner = CIRunner(
        workspace=tmp_path,
        commands=[
            f'"{PY}" -c "import sys; sys.exit(1)"',
            f'"{PY}" -c "print(1)"',
        ],
    )

    results = runner.run()

    assert len(results) == 1
    assert results[0].passed is False


def test_runs_all_commands_when_they_pass(tmp_path):
    runner = CIRunner(
        workspace=tmp_path,
        commands=[
            f'"{PY}" -c "print(1)"',
            f'"{PY}" -c "print(2)"',
        ],
    )

    results = runner.run()

    assert len(results) == 2
    assert CIRunner.all_passed(results) is True


def test_runs_in_the_given_workspace(tmp_path):
    marker = tmp_path / "marker.txt"

    runner = CIRunner(
        workspace=tmp_path,
        commands=[f'"{PY}" -c "open(\'marker.txt\', \'w\').write(\'hi\')"'],
    )
    runner.run()

    assert marker.exists()


def test_emits_ci_events(tmp_path):
    events = EventBus()

    runner = CIRunner(
        workspace=tmp_path,
        commands=[f'"{PY}" -c "print(1)"'],
        events=events,
    )
    runner.run()

    event_types = [e.type for e in events.log]

    assert event_types == [EventType.CI_STARTED, EventType.CI_PASSED]


def test_emits_ci_failed_event(tmp_path):
    events = EventBus()

    runner = CIRunner(
        workspace=tmp_path,
        commands=[f'"{PY}" -c "import sys; sys.exit(1)"'],
        events=events,
    )
    runner.run()

    event_types = [e.type for e in events.log]

    assert event_types == [EventType.CI_STARTED, EventType.CI_FAILED]


def test_all_passed_empty_results_is_true():
    assert CIRunner.all_passed([]) is True
