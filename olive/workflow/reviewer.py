from abc import ABC, abstractmethod

from olive.state.project import Project
from olive.state.review import ReviewResult


class Reviewer(ABC):
    """Interface for Olive Framework review/designer agents."""

    @abstractmethod
    def review(self, project: Project) -> ReviewResult:
        """Inspect the implementation and return a verdict."""
        raise NotImplementedError
