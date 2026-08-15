from dataclasses import dataclass
from pathlib import Path


@dataclass
class Project:
    name: str
    goal: str
    requirements: list[str]
    constraints: list[str]
    path: Path
