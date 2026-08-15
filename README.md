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
  cli.py                      `olive` command: PROJECT.md -> plan -> execute
  events.py                   EventType/Event/EventBus -- structured event log
  ui.py                       Live terminal dashboard (rich-based), driven by events
  state/
    parser.py                PROJECT.md parser
    project.py                Parsed project data
    task.py / task_graph.py   Internal task graph + dependency validation
    task_state.py / execution.py
  orchestrator/
    engine.py                 Runs a task graph to completion via an Executor,
                               emitting events as it goes
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
an executor interface (fake + real OpenHands-backed), a structured event bus,
a live terminal dashboard, and an `olive` CLI that chains all of it together.
Ported from an earlier local prototype and rebranded.

The Qwen/OpenHands executor path has been verified end-to-end against a real
local Ollama server on this machine (see `tests/test_real_orchestration.py`).
The DeepSeek/Ollama planner path is implemented and unit-tested but live
verification against `deepseek-r1:8b` on this machine's 6GB-VRAM GPU is
still in progress -- reasoning-model latency and JSON-mode output reliability
are both open questions being tracked, not yet resolved.

Not yet built: a Reviewer/Designer agent with browser/MCP-based visual
inspection, a CI/completion gate that actually runs tests against the
generated project, auto-generated knowledge docs (`plan.md`,
`design.md`, `review.md`, ...), durable persistence/recovery, and
pause/resume/approve human controls. See `FORGE_PROJECT_SPEC.md` for the
full intended scope.

## Running tests

```
pip install -e ".[dev]"
pytest
```

Tests in `test_openhands_executor.py` and `test_real_orchestration.py`
exercise a real OpenHands agent against a local Ollama server and require
the `openhands` optional dependency group plus a running Ollama instance
serving the configured model (defaults to `qwen3:8b`). They're skipped
automatically if `openhands` isn't installed. Everything else runs with no
external services.

The `openhands` SDK requires Python 3.12 (it does not yet support 3.13+).
Set up a separate interpreter for it, e.g. with `uv`:

```
uv venv --python 3.12 .venv312
uv pip install --python .venv312/Scripts/python.exe -e ".[dev,openhands]"
.venv312/Scripts/python.exe -m pytest
```

## Running the CLI

The `olive` command parses a `PROJECT.md`, plans it into a task graph, and
(unless `--dry-run` is given) executes every task in dependency order.

```
olive projects/demo/PROJECT.md --dry-run
```

Fully wired to local models (requires Ollama running with `deepseek-r1:8b`
and `qwen3:8b` pulled, and the `openhands` extra installed):

```
olive path/to/PROJECT.md --planner deepseek --executor openhands
```

Flags:

- `--planner {mock,deepseek}` (default `mock`) -- `mock` returns a fixed
  3-task plan; `deepseek` calls a local DeepSeek model through Ollama.
- `--executor {fake,openhands}` (default `fake`) -- `fake` marks every task
  completed without touching the filesystem; `openhands` runs a real
  OpenHands agent (Qwen by default) against the workspace.
- `--workspace PATH` -- execution workspace for the `openhands` executor
  (default: the PROJECT.md's parent directory).
- `--planner-model`, `--coder-model`, `--ollama-url` -- override the
  defaults (`deepseek-r1:8b`, `qwen3:8b`, `http://localhost:11434`).
- `--ui` -- show a live terminal dashboard (project/goal, task table with
  live status, current task, recent event log) instead of plain log lines.
- `--events-log PATH` -- write the full structured event log as JSON lines
  once the run finishes (works with or without `--ui`).
