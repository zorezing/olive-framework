from pathlib import Path

from openhands.sdk import Agent, Conversation, LLM
from openhands.tools.preset.default import get_default_tools

from olive.state.execution import TaskExecution
from olive.state.task import Task
from olive.state.task_state import TaskStatus
from olive.workflow.executor import Executor


class OpenHandsExecutor(Executor):
    def __init__(
        self,
        workspace: Path,
        model: str = "qwen3:8b",
        ollama_base_url: str = "http://localhost:11434",
        persistence_dir: Path | None = None,
    ):
        self.workspace = Path(workspace)
        self.persistence_dir = Path(persistence_dir) if persistence_dir else None

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

        conversation_kwargs = {}
        if self.persistence_dir is not None:
            conversation_kwargs["persistence_dir"] = str(
                self.persistence_dir / task.id
            )

        conversation = Conversation(
            agent=agent,
            workspace=self.workspace,
            **conversation_kwargs,
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

Execute this task in the current project workspace, completing every
step yourself, one tool call after another, without stopping to ask
what to do next -- no one will answer.

Actually make the required changes using the available tools.
Do not merely explain what should be done.

After implementing the task:
1. Verify the changed files.
2. Run relevant tests when available.
3. Fix straightforward errors you encounter.
"""

    def _system_prompt(self) -> str:
        return f"""
You are Olive Framework's coding and execution agent, operating fully
autonomously. There is no human watching this conversation and no one
will respond to questions or offers of options -- if you stop to ask
"would you like me to..." or "should I...", the process hangs forever
and the task fails. Once given a task, keep calling tools yourself,
one after another, until it is genuinely done.

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
- Do not stop and ask for confirmation or direction at any point. Keep
  taking the next step yourself until the task is complete.
- If you use the file_editor tool's `create` command, it takes exactly
  `command="create"`, `path=<absolute path>`, `file_text=<full file
  content>`. The parameter for the new file's content is `file_text`,
  not `content`. Using `content` will fail validation.
"""
