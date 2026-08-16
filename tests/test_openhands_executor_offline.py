from pathlib import Path

import pytest

pytest.importorskip("openhands", reason="requires the openhands optional dependency")

from olive.workflow.executor import Executor
from olive.workflow.openhands_executor import OpenHandsExecutor


def test_is_an_executor(tmp_path):
    executor = OpenHandsExecutor(workspace=tmp_path)

    assert isinstance(executor, Executor)


def test_web_fetch_disabled_by_default(tmp_path):
    executor = OpenHandsExecutor(workspace=tmp_path)

    assert executor.enable_web_fetch is False


def test_web_fetch_disabled_does_not_touch_mcp(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(
        "olive.workflow.mcp_tools.build_web_fetch_mcp_config",
        lambda *a, **k: called.append(True) or {},
    )

    executor = OpenHandsExecutor(workspace=tmp_path, enable_web_fetch=False)

    assert called == []
    assert executor.mcp_config == {}


def test_web_fetch_enabled_sets_mcp_config(tmp_path, monkeypatch):
    fake_config = {"fetch": object()}
    monkeypatch.setattr(
        "olive.workflow.mcp_tools.build_web_fetch_mcp_config",
        lambda *a, **k: fake_config,
    )

    executor = OpenHandsExecutor(workspace=tmp_path, enable_web_fetch=True)

    assert executor.mcp_config == fake_config


def test_web_fetch_system_prompt_mentions_fetch_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "olive.workflow.mcp_tools.build_web_fetch_mcp_config", lambda *a, **k: {}
    )

    enabled = OpenHandsExecutor(workspace=tmp_path, enable_web_fetch=True)
    disabled = OpenHandsExecutor(workspace=tmp_path, enable_web_fetch=False)

    assert "you have a `fetch` tool" in enabled._system_prompt().lower()
    assert "you have a `fetch` tool" not in disabled._system_prompt().lower()


def test_web_fetch_agent_actually_constructs(tmp_path):
    # Regression test: the real build_web_fetch_mcp_config() (unmocked) must
    # produce something Agent(mcp_config=...) actually accepts. Agent tools
    # and MCP tools have distinct types (Tool spec vs MCPServer config) and
    # a prior version of this code put MCP tool objects directly into the
    # `tools` list, which pydantic rejected at construction with a
    # ValidationError -- Agent() validates eagerly and does not need a live
    # network connection to do so, so this catches the mismatch offline.
    from openhands.sdk import Agent

    executor = OpenHandsExecutor(workspace=tmp_path, enable_web_fetch=True)

    Agent(
        llm=executor.llm,
        tools=executor.tools,
        mcp_config=executor.mcp_config,
        system_prompt=executor._system_prompt(),
    )
