import sys
from pathlib import Path

from olive.cli import main


PROJECT_FILE = Path("projects/demo/PROJECT.md")
PY = sys.executable


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


def test_unknown_project_file_prints_clean_error(capsys):
    exit_code = main(["projects/demo/DOES_NOT_EXIST.md", "--dry-run"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error:" in captured.out
    assert "DOES_NOT_EXIST.md" in captured.out


def test_malformed_project_file_prints_clean_error(tmp_path, capsys):
    bad_file = tmp_path / "PROJECT.md"
    bad_file.write_text("## Goal\nNo top-level heading here.", encoding="utf-8")

    exit_code = main([str(bad_file), "--dry-run"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error:" in captured.out


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


def test_passing_ci_command_marks_project_complete(tmp_path):
    log_path = tmp_path / "events.jsonl"

    exit_code = main(
        [
            str(PROJECT_FILE),
            "--ci-command",
            f'"{PY}" -c "print(1)"',
            "--events-log",
            str(log_path),
        ]
    )

    assert exit_code == 0

    import json

    events = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    event_types = [e["type"] for e in events]

    assert "CI_STARTED" in event_types
    assert "CI_PASSED" in event_types
    assert "PROJECT_COMPLETED" in event_types


def test_failing_ci_command_fails_the_run(tmp_path, capsys):
    log_path = tmp_path / "events.jsonl"

    exit_code = main(
        [
            str(PROJECT_FILE),
            "--ci-command",
            f'"{PY}" -c "import sys; sys.exit(1)"',
            "--events-log",
            str(log_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "CI failed." in captured.out

    import json

    events = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    event_types = [e["type"] for e in events]

    assert "CI_FAILED" in event_types
    assert "PROJECT_COMPLETED" not in event_types


def test_ci_commands_run_in_the_workspace(tmp_path):
    marker = tmp_path / "ci_marker.txt"

    exit_code = main(
        [
            str(PROJECT_FILE),
            "--workspace",
            str(tmp_path),
            "--ci-command",
            f'"{PY}" -c "open(\'ci_marker.txt\', \'w\').write(\'hi\')"',
        ]
    )

    assert exit_code == 0
    assert marker.exists()


def test_mock_reviewer_approves_and_completes_project(tmp_path):
    log_path = tmp_path / "events.jsonl"

    exit_code = main(
        [
            str(PROJECT_FILE),
            "--reviewer",
            "mock",
            "--events-log",
            str(log_path),
        ]
    )

    assert exit_code == 0

    import json

    events = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    event_types = [e["type"] for e in events]

    assert "REVIEW_STARTED" in event_types
    assert "REVIEW_CREATED" in event_types
    assert "PROJECT_COMPLETED" in event_types

    review_created = next(e for e in events if e["type"] == "REVIEW_CREATED")
    assert review_created["payload"]["approved"] is True


def test_no_reviewer_by_default(tmp_path):
    log_path = tmp_path / "events.jsonl"

    exit_code = main([str(PROJECT_FILE), "--events-log", str(log_path)])

    assert exit_code == 0

    import json

    events = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").strip().splitlines()
    ]
    event_types = [e["type"] for e in events]

    assert "REVIEW_STARTED" not in event_types
    assert "PROJECT_COMPLETED" in event_types


def test_deepseek_planner_requires_reachable_ollama():
    import pytest

    with pytest.raises(SystemExit):
        main(
            [
                str(PROJECT_FILE),
                "--planner",
                "deepseek",
                "--dry-run",
                "--ollama-url",
                "http://localhost:1",
            ]
        )


def test_dry_run_skips_ollama_check_even_for_openhands_executor():
    # --dry-run never reaches execution, so the openhands executor's Ollama
    # dependency should not be checked at all.
    exit_code = main(
        [
            str(PROJECT_FILE),
            "--executor",
            "openhands",
            "--dry-run",
            "--ollama-url",
            "http://localhost:1",
        ]
    )

    assert exit_code == 0


def test_fake_executor_with_mock_planner_never_needs_ollama():
    exit_code = main(
        [str(PROJECT_FILE), "--ollama-url", "http://localhost:1"]
    )

    assert exit_code == 0


def test_keyboard_interrupt_is_handled_gracefully(monkeypatch):
    from olive.orchestrator.engine import Orchestrator

    def raise_interrupt(self):
        raise KeyboardInterrupt

    monkeypatch.setattr(Orchestrator, "run", raise_interrupt)

    exit_code = main([str(PROJECT_FILE)])

    assert exit_code == 130


def test_keyboard_interrupt_mentions_resume_with_state_dir(tmp_path, capsys):
    from olive.orchestrator.engine import Orchestrator
    import pytest

    def raise_interrupt(self):
        raise KeyboardInterrupt

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(Orchestrator, "run", raise_interrupt)

        exit_code = main(
            [str(PROJECT_FILE), "--state-dir", str(tmp_path / "state")]
        )

    captured = capsys.readouterr()

    assert exit_code == 130
    assert "--resume" in captured.out


def test_ollama_reviewer_requires_reachable_ollama():
    import pytest

    with pytest.raises(SystemExit):
        main(
            [
                str(PROJECT_FILE),
                "--reviewer",
                "ollama",
                "--ollama-url",
                "http://localhost:1",
            ]
        )


def test_review_url_requires_openhands_reviewer():
    import pytest

    with pytest.raises(SystemExit):
        main(
            [
                str(PROJECT_FILE),
                "--reviewer",
                "ollama",
                "--review-url",
                "http://localhost:3000",
            ]
        )


def test_failing_ci_command_prints_its_output(capsys):
    exit_code = main(
        [
            str(PROJECT_FILE),
            "--ci-command",
            f'"{PY}" -c "print(\'boom details here\'); import sys; sys.exit(1)"',
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "boom details here" in captured.out
