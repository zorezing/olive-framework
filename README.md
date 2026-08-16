# Olive Framework

A local-first autonomous software-development system. The human provides a
Markdown project specification (`PROJECT.md`); Olive Framework plans the
project, builds an internal task graph, executes tasks through OpenHands,
runs tests, inspects the running application, researches solutions, reviews
the implementation, and iterates until the project satisfies its
requirements.

See `FORGE_PROJECT_SPEC.md` (project owner's copy) for the full design.

## Quickstart

```
pip install -e .
olive projects/demo/PROJECT.md --dry-run
```

That runs entirely offline (mock planner, no execution) just to confirm
the install works. To actually build something with local models, you
need [Ollama](https://ollama.com) running with `qwen3:8b` pulled
(`ollama pull qwen3:8b`), plus the `openhands` extra installed in a
**Python 3.12** environment (see "Running tests" below) if you want real
code execution rather than a dry-run plan:

```
olive path/to/your/PROJECT.md \
  --planner deepseek --planner-model qwen3:8b \
  --executor openhands --coder-model qwen3:8b \
  --reviewer ollama \
  --ui \
  --state-dir path/to/your/PROJECT/.olive
```

Write `PROJECT.md` yourself first -- see `projects/demo/PROJECT.md` for
the expected shape (`# Project`, `## Goal`, `## Requirements`,
`## Constraints`). `--ui` shows a live terminal dashboard; drop it for
plain scrolling log lines instead. `--state-dir` means an interrupted run
can be continued with `--resume` instead of starting over. See "Running
the CLI" below for every flag, and "Status" for what's actually been
live-verified to work vs. what's implemented-but-untested.

**Or skip flags entirely and browse projects interactively:** run
`olive` with no arguments (from wherever your PROJECT.md files live, or
pass `--projects-dir`) to open a numbered-menu launcher -- list every
project found, open one to see its goal/requirements/status, then
run/resume/create from there without remembering CLI flags. See
"Interactive launcher" below.

If you added the Python 3.12 environment's `Scripts` directory to your
PATH (see "Adding `olive` to PATH" below), all of the above works from
any terminal, in any directory, just by typing `olive`.

## Layout

```
olive/
  core.py                    Olive() app entry point
  cli.py                      `olive` command: PROJECT.md -> plan -> execute
  launcher.py                 Interactive project browser (`olive` with no args)
  events.py                   EventType/Event/EventBus -- structured event log
  ui.py                       Live terminal dashboard (rich-based), driven by events
  persistence.py               StateStore: streams events + task status to
                               disk for --state-dir / --resume
  knowledge.py                 KnowledgeStore: plan.md/decisions.md/
                               reviews/ durable docs, also under --state-dir
  ci.py                        CIRunner: runs --ci-command(s) as a
                               completion gate after all tasks finish
  safety.py                    is_dangerous_command(): heuristic guard,
                               used by CIRunner before running a command
  context.py                   rank_files_by_relevance(): lightweight
                               local (no-model) file relevance ranking
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
    reviewer.py / mock_reviewer.py / simple_reviewer.py /
      openhands_reviewer.py
    ollama_client.py           Minimal Ollama HTTP client
    planner_output.py          Planner JSON -> TaskGraph
    json_extraction.py         Shared JSON-from-chat-response extraction
                               (fenced blocks, <think> stripping, etc.)
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
local Ollama server on this machine (see `tests/test_real_orchestration.py`),
and re-confirmed with no regression after later prompt changes (both tests
still pass, ~90s-3min each). **But reliability here is task-granularity
dependent.** Every executor test that's passed gave the model a single,
fully-specified task: "create this exact file with this exact content." A
live full-pipeline run (5-task plan for a small calculator CLI, one task
per file/concern) got stuck instead: given an open-ended task ("implement
calculator.py") that requires the model to *decide* what code to write, not
just transcribe given content, `qwen3:8b` spent 10+ minutes reasoning in
circles -- hallucinating a "user" conversation that never happened,
marking a `task_tracker` entry "done" without writing any code, generally
losing the thread. This is a different, deeper failure mode than the
planner/reviewer issues above (which had non-agentic fixes); the executor
fundamentally needs sustained multi-step agentic tool use, and that's
where this model's reliability ceiling is on this hardware. If you hit
this: keep tasks maximally granular in `PROJECT.md` (spell out exact
file/function boundaries rather than "implement X"), use `--max-retries`
and `--state-dir`/`--resume` so a stuck task doesn't lose everything else,
and expect to supervise/intervene on genuinely open-ended implementation
tasks rather than trusting a fully unattended run.

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

**The reviewer went through the same investigation, with a different
conclusion.** `OpenHandsReviewer` (agentic, tool-calling, browser-capable)
was tested live five times against a minimal real workspace, with
`qwen3:8b`. Every attempt failed to produce `review.json`, via three
distinct failure modes across the iterations:
1. Given a choice between `terminal` and `file_editor`, it picked
   `file_editor` and never found the right parameter name for the
   `create` command (`file_text`, not the `content`/`file_path` it kept
   guessing) across 4 tries, then gave up.
2. Steered to `terminal`-only, it skipped tool calls entirely and
   reasoned hypothetically ("let's assume hello.py exists... this is a
   simulation") instead of actually inspecting anything.
3. Steered further with an explicit numbered-steps prompt plus retries,
   it reliably called one tool correctly (e.g. `Get-ChildItem`), then
   stopped and asked "would you like me to review the files?" -- treating
   an autonomous task as an interactive chat. This exact pattern repeated
   in **3 independent retry attempts within the same run**, and survived
   adding explicit "you are autonomous, no one will respond, never ask
   permission" framing at both the system-prompt and task-prompt level.
   That's a real capability limit for this model at this size on
   open-ended multi-step agentic tasks, not a wording problem.

The fix was architectural, not more prompt tuning: **`SimpleReviewer`**
reads the workspace's files itself in plain Python and asks a single
bounded Ollama chat completion for a JSON verdict -- exactly the pattern
already proven reliable for the planner, with no agentic tool-calling loop
for the model to get lost in. Live-tested twice against real workspaces
(one satisfying the requirements, one deliberately violating one) and
correctly approved/rejected both, with an accurate, specific finding in
the rejection case, zero retries needed either time. **`--reviewer
ollama` (`SimpleReviewer`) is the reliable, recommended default now.**
`OpenHandsReviewer` remains available as `--reviewer openhands` and is
still the only option when `--review-url` is given -- there's no way
around needing an agent with browser tools for actually visiting and
screenshotting a running application, and that specific browser-driving
path hasn't been live-tested yet (there's no generated application in
this repo to point it at). Given the pattern above, expect the same
kind of agentic unreliability there until proven otherwise.

Failure handling: a failing task is retried up to `--max-retries` times,
and a task that ultimately fails no longer aborts the whole run --
independent tasks keep going, only tasks that (transitively) depend on the
failure are left blocked. Ctrl+C is caught and exits cleanly (exit code
130) instead of a raw traceback, and if `--state-dir` was set it tells you
to `--resume`. A pre-flight check confirms Ollama is actually reachable
before `--planner deepseek` / `--executor openhands` / `--reviewer
openhands` do anything, with a clear error instead of a buried connection
traceback.

Durable knowledge docs, interactive human controls, and an interactive
project launcher are now built (see their own sections below). A
`--ci-command` is checked against a heuristic dangerous-command guard
(`olive/safety.py`) before it runs -- refuses obviously destructive
patterns (`rm -rf /`, `Remove-Item -Recurse -Force` on a drive root,
`format`, fork bombs, ...) rather than executing them; this is a safety
net against self-inflicted typos in commands you supplied yourself, not
a security sandbox, and is documented as such in the module. `SimpleReviewer`
ranks candidate files by relevance to the project's requirements/
constraints (`olive/context.py`, a local term-frequency scorer, no new
model or dependency) before truncating to its file budget, rather than
an arbitrary filesystem-order cutoff.

Still not built: `architecture.md`/`design.md`/a `research/` directory
from the original spec's knowledge layout -- nothing in this codebase
produces architecture decisions or research findings independent of the
plan/review content `KnowledgeStore` already captures, and empty
placeholder files for capabilities that don't exist would be worse than
not having them. See `FORGE_PROJECT_SPEC.md` for the full intended scope.

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
- `--reviewer {none,mock,ollama,openhands}` (default `none`) -- once tasks
  and CI pass, run this reviewer as the final completion gate.
  - `ollama` (**recommended**, live-verified reliable): reads the
    workspace's files itself and asks one bounded Ollama chat completion
    for a JSON verdict. No agentic tool use, no `openhands` dependency.
  - `openhands`: a real OpenHands agent with its browser tool enabled,
    for when `--review-url` is given (inspects a running app, not just
    source). Live-tested *unreliable* for source-only review with
    `qwen3:8b` -- see Status above -- so only reach for this when you
    actually need `--review-url`.
  - Either way: the reviewer writes/produces a verdict with `approved`,
    `findings` (each with a `blocking` flag), and `notes`. If it fails to
    produce a valid verdict (missing/malformed `review.json` for
    `openhands`, or repeated bad output for `ollama`), the review is
    treated as failed -- fail closed, not open.
- `--review-model` (default `qwen3:8b`) -- the project spec assumed
  DeepSeek would fill this role, but only `qwen3:8b` has actually been
  verified reliable for this project's local-model roles (planning,
  OpenHands tool-calling, review) -- see Status above.
- `--review-url URL` -- URL of a running instance of the generated
  application, for the `openhands` reviewer to visit with its browser
  tool and screenshot before forming a verdict. Requires `--reviewer
  openhands` (`ollama` can't browse).
- `--max-retries N` (default `0`) -- retry a failing task up to N times
  before giving up on it. Independent tasks still run either way; only
  tasks depending on a permanently failed one are blocked.
- `--interactive` -- prompt before each task (`[Y]es / [s]kip / [a]bort`),
  and offer `[r]etry / [o]verride / [a]bort` if CI or the reviewer reject
  the result, instead of running fully unattended. See "Interactive
  human controls" below.
- `--projects-dir PATH` (default: current directory) -- root to search
  for `PROJECT.md` files when `project` is omitted, launching the
  interactive browser. See "Interactive launcher" below.

## Durable knowledge docs

Whenever `--state-dir` is given, `KnowledgeStore` writes human-readable
project knowledge there as the run progresses, alongside the resume state:

- `plan.md` -- the current task graph (name, goal, planner used, every
  task with its dependencies). Regenerated each time planning completes,
  so it always reflects the latest plan, including after `--resume`
  replans.
- `decisions.md` -- an append-only, timestamped log of notable choices:
  which planner/executor/model were used, CI pass/fail, review verdicts,
  any `--interactive` overrides, final completion. Nothing is ever
  removed from it, so it reads as a project history across multiple runs.
- `reviews/review-NNN.md` + `.json` -- one numbered snapshot per review,
  never overwritten, so review history accumulates across runs. Built
  from the `ReviewResult` object itself, so it works uniformly whether
  you used `--reviewer ollama` or `--reviewer openhands` (the latter's
  own `review.json` in the *workspace* is a separate, single-run file
  the agent writes itself -- this is the durable copy).

## Interactive human controls

By default a run is fully unattended. Add `--interactive` for a human in
the loop:

- Before each task, you're asked `About to run TASK-003: Add tests.
  [Y]es / [s]kip / [a]bort?`. Skipping marks the task `SKIPPED` (not
  `COMPLETED` -- shows up distinctly in `--ui` and in `decisions.md`) but
  still unblocks anything that depended on it, on the assumption you
  handled it some other way; a skip is remembered across `--resume` just
  like a completion. Abort stops the whole run immediately, before that
  task starts, the same way Ctrl+C does (exit code 130, `--state-dir`
  progress is preserved).
- If a `--ci-command` fails, or the reviewer rejects the result, you're
  asked `[r]etry / [o]verride / [a]bort`. Retry re-runs the same gate;
  override is your explicit authority to accept the result anyway despite
  the tool's own gate saying no (recorded in `decisions.md`, not silent);
  abort stops the run.

## Interactive launcher

Run `olive` with no `PROJECT.md` argument to open a numbered-menu project
browser instead of executing anything directly:

```
olive --projects-dir path/to/your/projects
```

It recursively finds every `PROJECT.md` under that root (default: current
directory), skipping the usual noise directories (`.git`, `node_modules`,
`.venv`, etc.), and shows each one's name, goal, and status (`not started`
/ `in progress` / `needs attention` / `completed`, derived from
`<project-dir>/.olive/task_state.json` if present). Selecting a project
lets you:

- **run** it -- prompts for planner/executor/reviewer choices (with
  sensible defaults) and whether to show `--ui`, then calls the exact
  same `olive.cli.main()` the direct CLI invocation would, with
  `--state-dir <project-dir>/.olive` automatically set. Not a separate
  code path from the tested pipeline.
- **resume** it (shown once a `.olive` state directory exists) -- the
  same flow with `--resume` added.
- **view its knowledge docs** -- `plan.md`, `decisions.md`, and the
  latest review, right there in the menu.
- **create a new project** from the top-level menu (`n`) -- prompts for a
  directory name, project name, goal, requirements, and constraints, and
  writes a properly-formatted `PROJECT.md`.

This is a simple numbered-menu design (rich for display, `input()` for
interaction), not a full mouse/arrow-key TUI framework -- kept
dependency-light and easy to test by construction.

## Adding `olive` to PATH

To run `olive` from any directory without activating a venv first, add
the Python 3.12 environment's `Scripts` directory to your **User** PATH
(Windows; adjust for other platforms):

```powershell
$venvScripts = "path\to\olive-framework\.venv312\Scripts"
$current = [Environment]::GetEnvironmentVariable("PATH", "User")
[Environment]::SetEnvironmentVariable("PATH", "$current;$venvScripts", "User")
```

Open a new terminal afterward -- existing ones won't see the change. This
points `olive` at the fully-capable environment (`openhands` extra
installed), so `--executor openhands` and `--reviewer openhands` work
immediately, not just the mock/fake path.
