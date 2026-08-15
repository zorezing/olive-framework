import json

import pytest

pytest.importorskip("openhands", reason="requires the openhands optional dependency")

from olive.workflow.openhands_reviewer import OpenHandsReviewer


def test_constructs_with_browser_enabled(tmp_path):
    reviewer = OpenHandsReviewer(workspace=tmp_path)

    tool_names = {tool.name for tool in reviewer.tools}

    assert "browser_tool_set" in tool_names


def test_read_verdict_missing_file_is_not_approved(tmp_path):
    reviewer = OpenHandsReviewer(workspace=tmp_path)

    result = reviewer._read_verdict()

    assert result.approved is False
    assert len(result.findings) == 1
    assert result.findings[0].blocking is True


def test_read_verdict_invalid_json_is_not_approved(tmp_path):
    (tmp_path / "review.json").write_text("not json", encoding="utf-8")

    reviewer = OpenHandsReviewer(workspace=tmp_path)
    result = reviewer._read_verdict()

    assert result.approved is False
    assert len(result.findings) == 1


def test_read_verdict_parses_valid_approval(tmp_path):
    (tmp_path / "review.json").write_text(
        json.dumps(
            {
                "approved": True,
                "findings": [],
                "notes": "Looks good.",
            }
        ),
        encoding="utf-8",
    )

    reviewer = OpenHandsReviewer(workspace=tmp_path)
    result = reviewer._read_verdict()

    assert result.approved is True
    assert result.findings == []
    assert result.notes == "Looks good."


def test_read_verdict_parses_blocking_findings(tmp_path):
    (tmp_path / "review.json").write_text(
        json.dumps(
            {
                "approved": False,
                "findings": [
                    {"summary": "Missing auth check", "blocking": True},
                    {"summary": "Inconsistent spacing", "blocking": False},
                ],
                "notes": "Needs work.",
            }
        ),
        encoding="utf-8",
    )

    reviewer = OpenHandsReviewer(workspace=tmp_path)
    result = reviewer._read_verdict()

    assert result.approved is False
    assert len(result.findings) == 2
    assert result.findings[0].blocking is True
    assert result.findings[1].blocking is False


def test_persistence_dir_wired_through(tmp_path):
    persist_dir = tmp_path / "persist"

    reviewer = OpenHandsReviewer(workspace=tmp_path, persistence_dir=persist_dir)

    assert reviewer.persistence_dir == persist_dir
