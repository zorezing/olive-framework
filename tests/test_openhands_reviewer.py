import json

import pytest

pytest.importorskip("openhands", reason="requires the openhands optional dependency")

from olive.workflow.openhands_reviewer import OpenHandsReviewer


def test_constructs_with_browser_enabled(tmp_path):
    reviewer = OpenHandsReviewer(workspace=tmp_path)

    tool_names = {tool.name for tool in reviewer.tools}

    assert "browser_tool_set" in tool_names


def test_read_verdict_missing_file_returns_none(tmp_path):
    reviewer = OpenHandsReviewer(workspace=tmp_path)

    result = reviewer._read_verdict()

    assert result is None


def test_read_verdict_invalid_json_returns_none(tmp_path):
    (tmp_path / "review.json").write_text("not json", encoding="utf-8")

    reviewer = OpenHandsReviewer(workspace=tmp_path)
    result = reviewer._read_verdict()

    assert result is None


def test_read_verdict_non_dict_json_returns_none(tmp_path):
    (tmp_path / "review.json").write_text("[1, 2, 3]", encoding="utf-8")

    reviewer = OpenHandsReviewer(workspace=tmp_path)
    result = reviewer._read_verdict()

    assert result is None


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


def test_max_attempts_defaults_to_3(tmp_path):
    reviewer = OpenHandsReviewer(workspace=tmp_path)

    assert reviewer.max_attempts == 3


def test_review_retries_until_review_json_appears(tmp_path, monkeypatch):
    reviewer = OpenHandsReviewer(workspace=tmp_path, max_attempts=3)

    calls = []

    def fake_run_conversation(project, attempt):
        calls.append(attempt)
        if attempt == 2:
            (tmp_path / "review.json").write_text(
                json.dumps({"approved": True, "findings": [], "notes": "ok"}),
                encoding="utf-8",
            )

    monkeypatch.setattr(reviewer, "_run_conversation", fake_run_conversation)

    result = reviewer.review(project=object())

    assert calls == [1, 2]
    assert result.approved is True


def test_review_does_not_retry_a_legitimate_rejection(tmp_path, monkeypatch):
    (tmp_path / "review.json").write_text(
        json.dumps(
            {
                "approved": False,
                "findings": [{"summary": "missing tests", "blocking": True}],
                "notes": "not done yet",
            }
        ),
        encoding="utf-8",
    )

    reviewer = OpenHandsReviewer(workspace=tmp_path, max_attempts=3)

    calls = []
    monkeypatch.setattr(
        reviewer, "_run_conversation", lambda project, attempt: calls.append(attempt)
    )

    result = reviewer.review(project=object())

    assert calls == [1]
    assert result.approved is False
    assert result.findings[0].summary == "missing tests"


def test_review_gives_up_after_max_attempts(tmp_path, monkeypatch):
    reviewer = OpenHandsReviewer(workspace=tmp_path, max_attempts=3)

    calls = []
    monkeypatch.setattr(
        reviewer, "_run_conversation", lambda project, attempt: calls.append(attempt)
    )

    result = reviewer.review(project=object())

    assert calls == [1, 2, 3]
    assert result.approved is False
    assert "3 attempt" in result.findings[0].summary
