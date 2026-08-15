from abc import ABC, abstractmethod

from olive.state.project import Project
from olive.state.task_graph import TaskGraph


class Planner(ABC):
    """Interface for Olive Framework planning agents."""

    @abstractmethod
    def create_plan(self, project: Project) -> TaskGraph:
        """Generate an internal task graph from a project."""
        raise NotImplementedError
