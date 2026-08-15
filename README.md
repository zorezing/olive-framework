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
an executor interface (fake + real OpenHands-backed), and an `olive` CLI
that chains all four together. Ported from an earlier local prototype and
rebranded.

The full local pipeline (DeepSeek planner + Qwen/OpenHands executor, both
via a local Ollama server) has been verified to run end-to-end on this
machine -- see "Running the CLI" below.

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
