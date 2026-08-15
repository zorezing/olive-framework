from abc import ABC, abstractmethod

from olive.state.execution import TaskExecution
from olive.state.task import Task


class Executor(ABC):
    """Interface for agents that execute Olive Framework tasks."""

    @abstractmethod
    def execute(self, task: Task) -> TaskExecution:
        raise NotImplementedError
