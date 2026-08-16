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
  persistence.py               StateStore: streams events + task status to
                               disk for --state-dir / --resume
  ci.py                        CIRunner: runs --ci-command(s) as a
                               completion gate after all tasks finish
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
    reviewer.py / mock_reviewer.py / openhands_reviewer.py
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
an executor interface (fake + real OpenHands-backed), a reviewer interface
(mock + OpenHands-backed, browser tool enabled), a structured event bus, a
live terminal dashboard, a persistence/resume layer, a CI completion gate,
and an `olive` CLI that chains all of it together. Ported from an earlier
local prototype and rebranded.

The Qwen/OpenHands executor path has been verified end-to-end against a real
local Ollama server on this machine (see `tests/test_real_orchestration.py`).

The DeepSeek/Ollama planner path (`--planner deepseek`) is now **verified
end-to-end live**, planning the demo project into a clean, valid 16-task
graph through the real `olive` CLI. Getting there took real investigation:
`deepseek-r1:8b`, the model the project spec originally envisioned for
this role, turned out to be unreliable on this machine's 6GB-VRAM GPU --
across four live attempts it either timed out (600s, then 1800s) or
returned malformed content (a duplicate task ID) after ~15 minutes. Root
cause, confirmed by timing an identical trivial prompt on both models:
deepseek-r1:8b generates far more reasoning tokens (335 for the prompt
"ping" alone) at a similar tokens/sec to qwen3:8b, so its wall-clock cost
scales up badly. qwen3:8b -- already the only model verified reliable for
OpenHands tool-calling in this project (sec 13) -- was tested against the
identical real planner prompt and returned a valid plan in ~3m15s with no
retries needed. **`qwen3:8b` is therefore the default `--planner-model`**;
`deepseek-r1:8b` remains available by passing it explicitly, for hardware
that can sustain higher tokens/sec. `DeepSeekPlanner` also now caps
generation length (`num_predict`, default 4096) to bound worst-case
latency, and retries cover network/HTTP failures (timeouts, 500s) as well
as bad content, not just JSON/validation errors as before.

(A parallel hypothesis -- that Ollama's `format="json"` grammar constraint
was itself the source of the slowness -- was tested and disproven: Ollama
0.32.6 already separates a model's `<think>` trace from its constrained
`content` correctly, confirmed live, and disabling `format="json"` for
deepseek-r1:8b instead produced a hard 500 from Ollama's own server. That
setting (`json_mode`) is still exposed on `OllamaClient`/`DeepSeekPlanner`
in case a different model needs it, but stays on by default.)

The OpenHands reviewer's `browser_tool_set` availability is confirmed
offline; a full live visual-review run (navigating a real running app and
screenshotting it) hasn't been exercised yet since there's no generated
application in this repo to point it at. Given the planner findings above,
`--review-model` already defaulting to `qwen3:8b` (not `deepseek-r1:8b`)
looks like the right call for the same reliability reasons.

Failure handling: a failing task is retried up to `--max-retries` times,
and a task that ultimately fails no longer aborts the whole run --
independent tasks keep going, only tasks that (transitively) depend on the
failure are left blocked. Ctrl+C is caught and exits cleanly (exit code
130) instead of a raw traceback, and if `--state-dir` was set it tells you
to `--resume`. A pre-flight check confirms Ollama is actually reachable
before `--planner deepseek` / `--executor openhands` / `--reviewer
openhands` do anything, with a clear error instead of a buried connection
traceback.

Not yet built: auto-generated knowledge docs (`plan.md`, `design.md`,
`review.md` as durable project files rather than one-off review output),
and interactive approve/reject/skip controls (Ctrl+C + `--resume` covers
pause/resume; nothing prompts mid-run yet). See `FORGE_PROJECT_SPEC.md`
for the full intended scope.

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
  3-task plan; `deepseek` calls a local model through Ollama (despite the
  name, defaults to `qwen3:8b` -- see Status above).
- `--executor {fake,openhands}` (default `fake`) -- `fake` marks every task
  completed without touching the filesystem; `openhands` runs a real
  OpenHands agent (Qwen by default) against the workspace.
- `--workspace PATH` -- execution workspace for the `openhands` executor
  (default: the PROJECT.md's parent directory).
- `--planner-model` (default `qwen3:8b`), `--coder-model` (default
  `qwen3:8b`), `--ollama-url` (default `http://localhost:11434`) -- model/
  endpoint overrides. Pass `--planner-model deepseek-r1:8b` to use the
  model the spec originally envisioned for planning.
- `--ollama-timeout SECONDS` (default `900`) -- per-request timeout for
  the deepseek planner's Ollama calls.
- `--ui` -- show a live terminal dashboard (project/goal, task table with
  live status, current task, recent event log) instead of plain log lines.
- `--events-log PATH` -- write the full structured event log as JSON lines
  once the run finishes (works with or without `--ui`).
- `--state-dir PATH` -- stream task status and the event log to this
  directory as the run progresses (`task_state.json`, `events.jsonl`), and
  (for the `openhands` executor) give each task's OpenHands conversation
  its own persisted session under `PATH/openhands/<task-id>/`.
- `--resume` -- combined with `--state-dir` pointed at a prior run's
  directory, skip any task already recorded as completed there instead of
  re-executing it. Requires `--state-dir`.

Example: an interrupted run can be continued without redoing finished work:

```
olive path/to/PROJECT.md --executor openhands --state-dir path/to/PROJECT/.olive
# ...interrupted partway through...
olive path/to/PROJECT.md --executor openhands --state-dir path/to/PROJECT/.olive --resume
```

- `--ci-command CMD` (repeatable) -- after all tasks complete, run this
  shell command in the workspace as a completion gate (e.g. the generated
  project's own test/build command). Stops at the first failing command;
  the run's overall exit code reflects CI's result, not just task
  completion. `PROJECT_COMPLETED` only fires once every task *and* every
  CI command has passed (or no `--ci-command` was given at all).
- `--ci-timeout SECONDS` (default `600`) -- per-command timeout for
  `--ci-command`.
- `--reviewer {none,mock,openhands}` (default `none`) -- once tasks and CI
  pass, run this reviewer as the final completion gate. `openhands` uses a
  real OpenHands agent with its browser tool enabled to inspect the
  workspace (and, if `--review-url` is given, a running instance of the
  app) against the project's requirements/constraints, then writes
  `review.json` + `review.md` to the workspace; Olive reads `review.json`
  back for the pass/fail verdict. If the reviewer doesn't produce a valid
  `review.json`, the review is treated as failed (fail closed, not open).
- `--review-model` (default `qwen3:8b`) -- the project spec assumed
  DeepSeek would fill this role, but only `qwen3:8b` has actually been
  verified to make reliable OpenHands tool calls in this project's
  history (see `FORGE_PROJECT_SPEC.md` sec 13), so that's the default
  here until DeepSeek's OpenHands tool-calling reliability is separately
  checked.
- `--review-url URL` -- URL of a running instance of the generated
  application, for the `openhands` reviewer to visit with its browser
  tool and screenshot before forming a verdict.
- `--max-retries N` (default `0`) -- retry a failing task up to N times
  before giving up on it. Independent tasks still run either way; only
  tasks depending on a permanently failed one are blocked.
