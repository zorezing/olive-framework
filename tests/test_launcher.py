import io
import json

from rich.console import Console

from olive.launcher import Launcher, discover_projects, _determine_status


def make_input(responses):
    it = iter(responses)

    def input_func(prompt=""):
        return next(it)

    return input_func


def make_console():
    return Console(file=io.StringIO(), force_terminal=False, width=100)


def write_project(dir_path, name="Demo", goal="Build a thing", requirements=None, constraints=None):
    dir_path.mkdir(parents=True, exist_ok=True)
    requirements = requirements or ["Req one"]
    constraints = constraints or ["Constraint one"]
    lines = [f"# {name}", "", "## Goal", "", goal, "", "## Requirements", ""]
    lines += [f"- {r}" for r in requirements]
    lines += ["", "## Constraints", ""]
    lines += [f"- {c}" for c in constraints]
    (dir_path / "PROJECT.md").write_text("\n".join(lines), encoding="utf-8")
    return dir_path / "PROJECT.md"


def test_discover_projects_finds_project_md(tmp_path):
    write_project(tmp_path / "proj1")

    entries = discover_projects(tmp_path)

    assert len(entries) == 1
    assert entries[0].name == "Demo"


def test_discover_projects_skips_noise_directories(tmp_path):
    write_project(tmp_path / "proj1")
    write_project(tmp_path / "node_modules" / "somepkg")
    write_project(tmp_path / ".git" / "hooks")

    entries = discover_projects(tmp_path)

    assert len(entries) == 1


def test_discover_projects_skips_malformed_project_md(tmp_path):
    good = tmp_path / "good"
    good.mkdir()
    (good / "PROJECT.md").write_text("no heading here", encoding="utf-8")

    entries = discover_projects(tmp_path)

    assert entries == []


def test_discover_projects_finds_multiple(tmp_path):
    write_project(tmp_path / "proj1", name="A")
    write_project(tmp_path / "proj2", name="B")

    entries = discover_projects(tmp_path)

    assert {e.name for e in entries} == {"A", "B"}


def test_status_not_started_when_no_state_dir(tmp_path):
    assert _determine_status(tmp_path / ".olive") == "not started"


def test_status_in_progress(tmp_path):
    state_dir = tmp_path / ".olive"
    state_dir.mkdir()
    (state_dir / "task_state.json").write_text(
        json.dumps({"TASK-001": "completed", "TASK-002": "pending"}),
        encoding="utf-8",
    )

    assert _determine_status(state_dir) == "in progress"


def test_status_completed(tmp_path):
    state_dir = tmp_path / ".olive"
    state_dir.mkdir()
    (state_dir / "task_state.json").write_text(
        json.dumps({"TASK-001": "completed", "TASK-002": "completed"}),
        encoding="utf-8",
    )

    assert _determine_status(state_dir) == "completed"


def test_status_completed_treats_skipped_as_done(tmp_path):
    state_dir = tmp_path / ".olive"
    state_dir.mkdir()
    (state_dir / "task_state.json").write_text(
        json.dumps({"TASK-001": "completed", "TASK-002": "skipped"}),
        encoding="utf-8",
    )

    assert _determine_status(state_dir) == "completed"


def test_status_needs_attention_when_a_task_failed(tmp_path):
    state_dir = tmp_path / ".olive"
    state_dir.mkdir()
    (state_dir / "task_state.json").write_text(
        json.dumps({"TASK-001": "completed", "TASK-002": "failed"}),
        encoding="utf-8",
    )

    assert _determine_status(state_dir) == "needs attention"


def test_quit_returns_immediately(tmp_path):
    launcher = Launcher(tmp_path, console=make_console(), input_func=make_input(["q"]))

    exit_code = launcher.run()

    assert exit_code == 0


def test_unrecognized_choice_does_not_crash(tmp_path):
    launcher = Launcher(
        tmp_path, console=make_console(), input_func=make_input(["bogus", "q"])
    )

    exit_code = launcher.run()

    assert exit_code == 0


def test_selecting_project_then_back_then_quit(tmp_path):
    write_project(tmp_path / "proj1")

    launcher = Launcher(
        tmp_path, console=make_console(), input_func=make_input(["1", "b", "q"])
    )

    exit_code = launcher.run()

    assert exit_code == 0


def test_create_project_writes_project_md(tmp_path):
    responses = [
        "n",  # command: new project
        "mydir",  # directory name
        "My Project",  # project name
        "Build something great",  # goal
        "Req A",  # requirement 1
        "",  # end requirements
        "Con A",  # constraint 1
        "",  # end constraints
        "",  # press enter to continue
        "q",  # quit
    ]
    launcher = Launcher(tmp_path, console=make_console(), input_func=make_input(responses))

    launcher.run()

    project_path = tmp_path / "mydir" / "PROJECT.md"
    assert project_path.exists()

    content = project_path.read_text(encoding="utf-8")
    assert "# My Project" in content
    assert "Build something great" in content
    assert "Req A" in content
    assert "Con A" in content


def test_create_project_cancelled_with_empty_dir_name(tmp_path):
    responses = ["n", "", "q"]
    launcher = Launcher(tmp_path, console=make_console(), input_func=make_input(responses))

    launcher.run()

    assert list(tmp_path.iterdir()) == []


def test_run_project_calls_cli_main_with_expected_argv(tmp_path, monkeypatch):
    project_path = write_project(tmp_path / "proj1")
    entry_state_dir = tmp_path / "proj1" / ".olive"

    captured_argv = []

    def fake_main(argv):
        captured_argv.append(argv)
        return 0

    import olive.cli
    monkeypatch.setattr(olive.cli, "main", fake_main)

    responses = [
        "1",  # select project
        "r",  # run
        "mock",  # planner
        "fake",  # executor
        "none",  # reviewer
        "n",  # no dashboard
        "",  # press enter to return
        "b",  # back
        "q",  # quit
    ]
    launcher = Launcher(tmp_path, console=make_console(), input_func=make_input(responses))
    launcher.run()

    assert len(captured_argv) == 1
    argv = captured_argv[0]
    assert argv[0] == str(project_path)
    assert "--planner" in argv and argv[argv.index("--planner") + 1] == "mock"
    assert "--executor" in argv and argv[argv.index("--executor") + 1] == "fake"
    assert "--reviewer" in argv and argv[argv.index("--reviewer") + 1] == "none"
    assert "--ui" not in argv
    assert "--state-dir" in argv
    assert argv[argv.index("--state-dir") + 1] == str(entry_state_dir)
    assert "--resume" not in argv


def test_resume_adds_resume_flag(tmp_path, monkeypatch):
    project_path = write_project(tmp_path / "proj1")
    state_dir = tmp_path / "proj1" / ".olive"
    state_dir.mkdir()
    (state_dir / "task_state.json").write_text(
        json.dumps({"TASK-001": "failed"}), encoding="utf-8"
    )

    captured_argv = []

    def fake_main(argv):
        captured_argv.append(argv)
        return 0

    import olive.cli
    monkeypatch.setattr(olive.cli, "main", fake_main)

    responses = [
        "1",
        "resume",
        "mock",
        "fake",
        "none",
        "n",
        "",
        "b",
        "q",
    ]
    launcher = Launcher(tmp_path, console=make_console(), input_func=make_input(responses))
    launcher.run()

    assert len(captured_argv) == 1
    assert "--resume" in captured_argv[0]
