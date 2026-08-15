from pathlib import Path

from openhands.sdk import Agent, Conversation, LLM
from openhands.tools.preset.default import get_default_tools

from olive.state.execution import TaskExecution
from olive.state.task import Task
from olive.state.task_state import TaskStatus


class OpenHandsExecutor:
    def __init__(
        self,
        workspace: Path,
        model: str = "qwen3:8b",
        ollama_base_url: str = "http://localhost:11434",
    ):
        self.workspace = Path(workspace)

        self.llm = LLM(
            model=f"openai/{model}",
            base_url=f"{ollama_base_url}/v1",
            api_key="ollama",
        )

        self.tools = get_default_tools(
            enable_browser=False,
            enable_sub_agents=False,
        )

    def execute(self, task: Task) -> TaskExecution:
        agent = Agent(
            llm=self.llm,
            tools=self.tools,
            system_prompt=self._system_prompt(),
        )

        conversation = Conversation(
            agent=agent,
            workspace=self.workspace,
        )

        conversation.send_message(
            self._build_prompt(task)
        )

        try:
            conversation.run()

            return TaskExecution(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                message="OpenHands completed the task.",
            )

        except Exception as exc:
            return TaskExecution(
                task_id=task.id,
                status=TaskStatus.FAILED,
                message=str(exc),
            )

    def _build_prompt(self, task: Task) -> str:
        return f"""
Olive Framework task:

ID: {task.id}
Title: {task.title}
Type: {task.task_type}

Description:
{task.description}

Execute this task in the current project workspace.

Actually make the required changes using the available tools.
Do not merely explain what should be done.

After implementing the task:
1. Verify the changed files.
2. Run relevant tests when available.
3. Fix straightforward errors you encounter.
"""

    def _system_prompt(self) -> str:
        return f"""
You are Olive Framework's coding and execution agent.

You operate on Windows.

Project workspace:
{self.workspace}

Terminal:
Windows PowerShell.

Rules:
- Actually execute work using the available tools.
- Do not merely describe commands.
- Use PowerShell, not bash or Linux commands.
- Never use Linux paths such as /workspace.
- Stay inside the project workspace.
- Verify important changes.
- Run relevant tests.
"""
