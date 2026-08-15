# Olive Framework

A local-first autonomous software-development system. The human provides a
Markdown project specification (`PROJECT.md`); Olive Framework plans the
project, builds an internal task graph, executes tasks through OpenHands,
runs tests, inspects the running application, researches solutions, reviews
the implementation, and iterates until the project satisfies its
requirements.

See `FORGE_PROJECT_SPEC.md` (project owner's copy) for the full design.

## Layout

```
olive/
  core.py                    Olive() app entry point
  state/
    parser.py                PROJECT.md parser
    project.py                Parsed project data
    task.py / task_graph.py   Internal task graph + dependency validation
    task_state.py / execution.py
  orchestrator/
    engine.py                 Runs a task graph to completion via an Executor
  workflow/
    planner.py / mock_planner.py / deepseek_planner.py
    executor.py / fake_executor.py / openhands_executor.py
    ollama_client.py           Minimal Ollama HTTP client
    planner_output.py          Planner JSON -> TaskGraph
    prompts.py

projects/demo/PROJECT.md      Example project spec used by the test suite
tests/                         Test suite mirroring the above
scripts/                       Manual OpenHands smoke-test scripts
```

## Status

Core loop foundation: Markdown project parser, task graph with dependency
validation, orchestrator, planner interface (mock + DeepSeek/Ollama-backed),
and an executor interface (fake + real OpenHands-backed). Ported from an
earlier local prototype and rebranded.

## Running tests

```
pip install -e ".[dev]"
pytest
```

Tests in `test_openhands_executor.py` and `test_real_orchestration.py`
exercise a real OpenHands agent against a local Ollama server and require
the `openhands` optional dependency group plus a running Ollama instance
serving the configured model (defaults to `qwen3:8b`). Everything else runs
with no external services.
