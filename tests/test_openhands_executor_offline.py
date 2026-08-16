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
        "olive.workflow.mcp_tools.build_web_fetch_tools",
        lambda *a, **k: called.append(True) or [],
    )

    OpenHandsExecutor(workspace=tmp_path, enable_web_fetch=False)

    assert called == []


def test_web_fetch_enabled_extends_tools(tmp_path, monkeypatch):
    fake_tool = object()
    monkeypatch.setattr(
        "olive.workflow.mcp_tools.build_web_fetch_tools",
        lambda *a, **k: [fake_tool],
    )

    executor = OpenHandsExecutor(workspace=tmp_path, enable_web_fetch=True)

    assert fake_tool in executor.tools


def test_web_fetch_system_prompt_mentions_fetch_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "olive.workflow.mcp_tools.build_web_fetch_tools", lambda *a, **k: []
    )

    enabled = OpenHandsExecutor(workspace=tmp_path, enable_web_fetch=True)
    disabled = OpenHandsExecutor(workspace=tmp_path, enable_web_fetch=False)

    assert "you have a `fetch` tool" in enabled._system_prompt().lower()
    assert "you have a `fetch` tool" not in disabled._system_prompt().lower()
