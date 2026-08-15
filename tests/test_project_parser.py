from pathlib import Path

import pytest

from olive.state.parser import ProjectParser


PROJECT_FILE = Path("projects/demo/PROJECT.md")


def test_project_file_exists():
    assert PROJECT_FILE.exists()


def test_parser_reads_project_name():
    parser = ProjectParser()

    project = parser.parse(PROJECT_FILE)

    assert project.name == "Project"


def test_parser_reads_goal():
    parser = ProjectParser()

    project = parser.parse(PROJECT_FILE)

    assert "web application" in project.goal


def test_parser_reads_requirements():
    parser = ProjectParser()

    project = parser.parse(PROJECT_FILE)

    assert "React frontend" in project.requirements
    assert "FastAPI backend" in project.requirements
    assert "PostgreSQL database" in project.requirements


def test_parser_reads_constraints():
    parser = ProjectParser()

    project = parser.parse(PROJECT_FILE)

    assert "Must run locally" in project.constraints
    assert "No cloud dependency" in project.constraints


def test_missing_project_file():
    parser = ProjectParser()

    with pytest.raises(FileNotFoundError):
        parser.parse("projects/demo/DOES_NOT_EXIST.md")

def test_parser_rejects_project_without_name(tmp_path):
    invalid_file = tmp_path / "PROJECT.md"
    invalid_file.write_text("## Goal\nBuild something.")

    parser = ProjectParser()

    with pytest.raises(ValueError):
        parser.parse(invalid_file)


def test_invalid_project_filename(tmp_path):
    invalid_file = tmp_path / "something.md"
    invalid_file.write_text("# Project")

    parser = ProjectParser()

    with pytest.raises(ValueError):
        parser.parse(invalid_file)
