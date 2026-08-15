from olive.state.project import Project
from olive.state.review import ReviewResult
from olive.workflow.reviewer import Reviewer


class MockReviewer(Reviewer):
    """Deterministic reviewer used for testing. Always approves."""

    def review(self, project: Project) -> ReviewResult:
        return ReviewResult(
            approved=True,
            findings=[],
            notes=f"Mock review of {project.name}: no issues found.",
        )
