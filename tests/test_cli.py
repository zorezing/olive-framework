from pathlib import Path

from olive.cli import main


PROJECT_FILE = Path("projects/demo/PROJECT.md")


def test_dry_run_prints_plan_without_executing(capsys):
    exit_code = main([str(PROJECT_FILE), "--dry-run"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "TASK-001" in captured.out
    assert "All tasks completed" not in captured.out


def test_default_run_plans_and_executes_with_mock_and_fake(capsys):
    exit_code = main([str(PROJECT_FILE)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Planned 3 task(s)" in captured.out
    assert "All tasks completed." in captured.out


def test_unknown_project_file_raises():
    import pytest

    with pytest.raises(FileNotFoundError):
        main(["projects/demo/DOES_NOT_EXIST.md", "--dry-run"])


def test_ui_mode_runs_without_raising():
    exit_code = main([str(PROJECT_FILE), "--ui"])

    assert exit_code == 0


def test_events_log_written_to_file(tmp_path):
    log_path = tmp_path / "events.jsonl"

    exit_code = main([str(PROJECT_FILE), "--events-log", str(log_path)])

    assert exit_code == 0
    assert log_path.exists()

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()

    assert len(lines) > 0

    import json

    first = json.loads(lines[0])
    assert first["type"] == "PROJECT_LOADED"


def test_resume_without_state_dir_is_rejected():
    import pytest

    with pytest.raises(SystemExit):
        main([str(PROJECT_FILE), "--resume"])


def test_state_dir_persists_task_state(tmp_path):
    state_dir = tmp_path / "state"

    exit_code = main([str(PROJECT_FILE), "--state-dir", str(state_dir)])

    assert exit_code == 0
    assert (state_dir / "task_state.json").exists()
    assert (state_dir / "events.jsonl").exists()

    import json

    statuses = json.loads((state_dir / "task_state.json").read_text(encoding="utf-8"))
    assert statuses == {
        "TASK-001": "completed",
        "TASK-002": "completed",
        "TASK-003": "completed",
    }


def test_resume_skips_already_completed_tasks(tmp_path):
    state_dir = tmp_path / "state"
    first_log = tmp_path / "first.jsonl"
    second_log = tmp_path / "second.jsonl"

    main(
        [
            str(PROJECT_FILE),
            "--state-dir",
            str(state_dir),
            "--events-log",
            str(first_log),
        ]
    )

    exit_code = main(
        [
            str(PROJECT_FILE),
            "--state-dir",
            str(state_dir),
            "--resume",
            "--events-log",
            str(second_log),
        ]
    )

    assert exit_code == 0

    import json

    second_events = [
        json.loads(line)
        for line in second_log.read_text(encoding="utf-8").strip().splitlines()
    ]
    task_started_events = [e for e in second_events if e["type"] == "TASK_STARTED"]

    assert task_started_events == []
