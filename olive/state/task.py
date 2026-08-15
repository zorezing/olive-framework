from dataclasses import dataclass, field


@dataclass
class Task:
    """A unit of work generated internally by Olive Framework."""

    id: str
    title: str
    description: str
    task_type: str
    dependencies: list[str] = field(default_factory=list)
