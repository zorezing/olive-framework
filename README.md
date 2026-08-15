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

The DeepSeek/Ollama planner path is implemented and thoroughly unit-tested
(fenced/think-wrapped JSON extraction, duplicate-ID and other validation
failures, network/HTTP-level retries), but has not yet completed a full
successful live run on this machine. Across several live attempts against
`deepseek-r1:8b` on this machine's 6GB-VRAM GPU:
- with `format="json"` (the default): one attempt timed out at 600s, one
  attempt returned a response after ~15 min that was valid-ish (markdown-
  fenced, contained a duplicate task ID) -- exactly the cases the parser
  and retry logic above were built to handle -- and one attempt timed out
  at 1800s with no response at all.
- with `format="json"` disabled (tried as a fix for the slowness): Ollama's
  server itself returned a 500 ("The model produced output that does not
  match the expected peg-native format") -- a template mismatch specific
  to this Ollama/model combination, not a client-side setting. Reverted;
  `format="json"` is the only mode that has ever produced usable content.

In short: the code path is believed correct and defensively handles every
failure mode observed so far, but `deepseek-r1:8b` on this hardware is
slow and inconsistent enough that a clean end-to-end confirmation is still
pending. The OpenHands reviewer's `browser_tool_set` availability is
confirmed offline; a full live visual-review run (navigating a real running
app and screenshotting it) hasn't been exercised yet since there's no
generated application in this repo to point it at.

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
