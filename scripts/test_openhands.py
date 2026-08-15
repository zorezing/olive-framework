from pathlib import Path

from openhands.sdk import Agent, Conversation, LLM
from openhands.tools.preset.default import get_default_tools


workspace = Path(__file__).resolve().parents[1]

llm = LLM(
    model="openai/qwen3:8b",
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

all_tools = get_default_tools(enable_browser=False)

terminal_tool = [
    tool for tool in all_tools
    if tool.name == "terminal"
]

agent = Agent(
    llm=llm,
    tools=terminal_tool,
)

conversation = Conversation(
    agent=agent,
    workspace=str(workspace),
)

conversation.send_message(
    f"""
You are operating on a Windows machine.

IMPORTANT:
- The terminal is Windows PowerShell.
- Use ONLY PowerShell commands.
- NEVER use bash, sh, Linux commands, or Linux paths.
- NEVER use /workspace.
- The workspace is exactly:
  {workspace}

Task:

1. Run this PowerShell command:

New-Item -Path "{workspace}\\OPENHANDS_TEST.txt" -ItemType File -Force

2. Write exactly this text into the file:

OpenHands is connected to Olive Framework.

3. Verify it using:

Get-Content "{workspace}\\OPENHANDS_TEST.txt"

Actually execute the commands using the terminal tool. Do not merely describe the commands.
"""
)

conversation.run()

print("OpenHands task completed.")
