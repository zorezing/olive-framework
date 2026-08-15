from pathlib import Path

from olive.state.parser import ProjectParser
from olive.state.review import Finding, ReviewResult
from olive.workflow.mock_reviewer import MockReviewer


PROJECT_FILE = Path("projects/demo/PROJECT.md")


def test_mock_reviewer_approves():
    project = ProjectParser().parse(PROJECT_FILE)

    result = MockReviewer().review(project)

    assert result.approved is True
    assert result.findings == []
    assert project.name in result.notes


def test_finding_defaults_to_blocking():
    finding = Finding(summary="Something is off")

    assert finding.blocking is True


def test_review_result_defaults():
    result = ReviewResult(approved=True)

    assert result.findings == []
    assert result.notes == ""
