from olive.state.project import Project
from olive.state.task import Task
from olive.state.task_graph import TaskGraph
from olive.workflow.planner import Planner


class MockPlanner(Planner):
    """Deterministic planner used for testing Olive Framework."""

    def create_plan(self, project: Project) -> TaskGraph:
        return TaskGraph(
            tasks=[
                Task(
                    id="TASK-001",
                    title="Initialize project",
                    description=(
                        f"Initialize the project for: {project.name}"
                    ),
                    task_type="infrastructure",
                ),
                Task(
                    id="TASK-002",
                    title="Implement core functionality",
                    description=(
                        "Implement the core functionality "
                        "described in the project requirements."
                    ),
                    task_type="implementation",
                    dependencies=["TASK-001"],
                ),
                Task(
                    id="TASK-003",
                    title="Add automated tests",
                    description="Create tests for the implementation.",
                    task_type="testing",
                    dependencies=["TASK-002"],
                ),
            ]
        )
