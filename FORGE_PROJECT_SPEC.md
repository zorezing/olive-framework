# FORGE --- Autonomous Local AI Software Development System

**Status:** Active development\
**Workspace:** `D:\AI\Projects\forge`

## 1. Vision

Forge is a local-first autonomous software-development system. The human
provides a Markdown project specification such as `PROJECT.md`; Forge
plans the project, builds an internal task graph, executes tasks through
OpenHands, runs tests/CI, visually inspects the running application,
researches solutions, reviews the implementation, and iterates until the
project satisfies its requirements.

The intended closed loop is:

``` text
PROJECT.md
   ↓
DeepSeek R1 — Planner / Architect
   ↓
Architecture + Task Graph
   ↓
Orchestrator
   ↓
Qwen 3:8B + OpenHands
   ↓
Code + Files + Terminal + Tests
   ↓
CI / Application
   ↓
Browser / MCP / Screenshots / Research
   ↓
DeepSeek R1 — Designer / Reviewer
   ↓
design.md / review.md / research/
   ↓
Qwen fixes
   ↓
CI
   ↓
Reviewer re-check
   ↓
DONE
```

The core philosophy is:

> **The human defines the goal. Specialized local agents plan,
> implement, inspect, review, test, and iterate.**

------------------------------------------------------------------------

# 2. Why Forge Exists

Forge is intended to be more than a local chatbot that writes code.

A normal coding assistant generally follows:

``` text
Human → prompt → model → code
```

Forge is intended to follow:

``` text
Human
  ↓
Requirements
  ↓
Planning
  ↓
Task decomposition
  ↓
Implementation
  ↓
Execution
  ↓
Testing
  ↓
Visual inspection
  ↓
Research
  ↓
Review
  ↓
Correction
  ↓
Testing
  ↓
Completion
```

The project should therefore behave more like a small autonomous
engineering team.

------------------------------------------------------------------------

# 3. Human Interface: Markdown First

The user should not have to manually define every task.

The primary interface is a Markdown file in the project directory:

``` text
PROJECT.md
```

For example:

``` markdown
# Project

## Goal

Create a local network monitoring dashboard.

## Requirements

- React frontend
- FastAPI backend
- PostgreSQL database
- Authentication
- Device discovery
- Network status dashboard
- Docker deployment

## Constraints

- Must run locally
- No cloud dependency
- API must be documented
- Major functionality requires tests
```

Forge reads this document and derives the implementation plan itself.

JSON/task objects remain internal representations. Markdown is the
human-facing project source of truth.

------------------------------------------------------------------------

# 4. Agent Organization

## 4.1 DeepSeek R1 --- Planner / Architect

Current intended model:

``` text
deepseek-r1:8b
```

The user has the abliterated DeepSeek model installed and intends to use
the abliterated variant for reasoning/review.

Responsibilities:

-   understand `PROJECT.md`
-   determine architecture
-   identify components
-   decompose requirements into concrete tasks
-   establish dependencies
-   identify integration points
-   make architectural decisions
-   write planning knowledge into Markdown
-   avoid implementation coding unless explicitly required

The Planner answers:

> **What should we build, in what order, and why?**

------------------------------------------------------------------------

## 4.2 Qwen 3:8B --- Coder / Execution Agent

Current selected model:

``` text
qwen3:8b
```

This model was selected after testing local models with OpenHands.

The installed `qwen3.5-abliterated:9b` was tested but did not reliably
produce the structured tool calls required by OpenHands. The normal
`qwen3:8b` successfully produced real OpenHands tool calls and created
files in the Windows workspace.

Responsibilities:

-   implement approved tasks
-   edit source files
-   create files
-   use terminal tools
-   run tests
-   inspect errors
-   fix implementation issues
-   verify changes
-   stay inside the project workspace

The Coder answers:

> **How do I implement this already-approved task?**

It should not repeatedly redesign the project from scratch.

------------------------------------------------------------------------

## 4.3 DeepSeek R1 --- Designer / Reviewer

The same DeepSeek family is intended for the design/review side.

Responsibilities:

-   inspect implementation
-   inspect running application
-   inspect screenshots
-   compare implementation with requirements/design
-   research better solutions
-   use browser/MCP capabilities
-   identify visual and functional issues
-   write `review.md`
-   update `design.md`
-   create research notes
-   generate corrective tasks

The Reviewer answers:

> **Is what we built actually correct, useful, and well designed?**

------------------------------------------------------------------------

# 5. High-Level Architecture

``` text
                         HUMAN
                           |
                           v
                     PROJECT.md
                           |
                           v
                 +------------------+
                 | DeepSeek Planner |
                 +------------------+
                           |
                           v
                  Architecture + Plan
                           |
                           v
                       TaskGraph
                           |
                           v
                    +-------------+
                    | Orchestrator|
                    +-------------+
                           |
                           v
                  +----------------+
                  | Qwen 3:8B      |
                  | Coder          |
                  +----------------+
                           |
                           v
                    OpenHands SDK
                 /        |                        /         |                        v          v          v
        File Editor    Terminal   Task Tracker
                \         |         /
                 \        |        /
                  v       v       v
                    Project Files
                           |
                           v
                       CI / Tests
                           |
                           v
                    Running Project
                           |
                           v
                   Browser / MCP
                           |
                           v
                 Screenshots + Research
                           |
                           v
                 DeepSeek Reviewer
                           |
                           v
                   review.md
                           |
                           v
                    Corrective Tasks
                           |
                           v
                    Qwen + OpenHands
                           |
                           v
                          CI
                           |
                         repeat
```

------------------------------------------------------------------------

# 6. Project Knowledge Structure

The intended project layout is:

``` text
project/
│
├── PROJECT.md
│
├── forge/
│   ├── plan.md
│   ├── architecture.md
│   ├── design.md
│   ├── review.md
│   ├── decisions.md
│   │
│   └── research/
│       ├── research-001.md
│       ├── research-002.md
│       └── ...
│
├── backend/
├── frontend/
├── tests/
└── ...
```

### `PROJECT.md`

Human-authored requirements.

### `plan.md`

Planner-generated implementation plan.

### `architecture.md`

Architecture decisions and component relationships.

### `design.md`

UI/UX and design decisions.

### `review.md`

Current reviewer findings and requested corrections.

### `decisions.md`

Important project decisions.

### `research/`

Evidence and useful findings collected by the Designer/Reviewer.

------------------------------------------------------------------------

# 7. Project Parser

Forge already contains a Markdown project parser.

It is responsible for:

-   locating the project file
-   validating its structure
-   extracting project name
-   extracting goal
-   extracting requirements
-   extracting constraints
-   rejecting invalid project definitions

Parser tests have already covered:

-   project file existence
-   project name parsing
-   goal parsing
-   requirements
-   constraints
-   missing project file
-   invalid filename
-   missing project name

An early heading-format mismatch was discovered and corrected during
development.

------------------------------------------------------------------------

# 8. Planner and Task Graph

The Planner converts the Markdown requirements into an internal task
graph.

Example:

``` text
Database
   |
   +------> Backend Foundation
                  |
                  +------> Authentication
                  |
                  +------> Device Discovery
                                  |
                                  v
                             Integration
                                  |
                                  v
                                Tests
```

Each task contains information such as:

-   ID
-   title
-   description
-   type
-   dependencies

The TaskGraph is responsible for determining which tasks are ready.

Typical states:

``` text
PENDING
READY
RUNNING
COMPLETED
FAILED
BLOCKED
```

A task cannot execute until its dependencies are satisfied.

The project already has tests for:

-   task lookup
-   task IDs
-   initial ready tasks
-   dependency handling
-   integration dependency ordering
-   circular dependencies
-   self-dependencies
-   duplicate IDs
-   unknown dependencies

------------------------------------------------------------------------

# 9. Orchestrator

The Orchestrator controls execution.

Conceptually:

``` python
while not graph.complete():

    ready = graph.ready_tasks()

    for task in ready:
        result = executor.execute(task)

        if result.success:
            graph.complete(task)
        else:
            graph.fail(task)
```

The eventual implementation will also handle:

-   retries
-   CI
-   reviewer cycles
-   failure recovery
-   events
-   model health
-   human intervention

The Orchestrator is the central coordination layer.

------------------------------------------------------------------------

# 10. OpenHands Integration

OpenHands is used as Forge's agent execution/tool layer.

Current tested version:

``` text
OpenHands SDK 1.42.1
```

Available OpenHands tools include:

``` text
terminal
file_editor
task_tracker
browser_tool_set
```

The current coder configuration intentionally disables browser tools.
Browser capabilities belong primarily to the Designer/Reviewer phase.

------------------------------------------------------------------------

# 11. OpenHandsExecutor

`OpenHandsExecutor` bridges:

``` text
Forge Task
    ↓
OpenHands
    ↓
Qwen 3:8B
    ↓
actual workspace
```

Current Ollama endpoint:

``` text
http://localhost:11434
```

OpenAI-compatible endpoint used by OpenHands:

``` text
http://localhost:11434/v1
```

Model configuration:

``` text
openai/qwen3:8b
```

The executor provides:

-   Qwen model
-   OpenHands tools
-   project workspace
-   Windows/PowerShell instructions
-   task description
-   execution result

------------------------------------------------------------------------

# 12. Windows Execution Environment

Forge is primarily developed on Windows using PowerShell.

Project workspace:

``` text
D:\AI\Projectsorge
```

OpenHands successfully auto-detected:

``` text
WindowsTerminal
PowerShell backend
```

The Coder system prompt explicitly states:

``` text
You operate on Windows.
The terminal is Windows PowerShell.
Do not use bash or Linux commands.
Never use Linux paths such as /workspace.
Stay inside the project workspace.
Actually execute work using the available tools.
Verify important changes.
Run relevant tests.
```

This was added because early model output attempted Linux-style paths
and commands.

------------------------------------------------------------------------

# 13. OpenHands Tool-Calling Findings

A major development finding was that local models do not all behave
equally with structured tool calling.

## Qwen 3:8B

``` text
qwen3:8b
```

Successfully demonstrated:

``` text
Qwen
 ↓
structured OpenHands tool call
 ↓
file_editor / terminal
 ↓
Windows filesystem
```

A real integration test created and verified a file through the
Orchestrator.

## Qwen 3.5 abliterated 9B

``` text
huihui_ai/qwen3.5-abliterated:9b
```

Testing showed unreliable structured OpenHands tool calling. It
sometimes generated tool-like markup as plain model text instead of
invoking the actual tool interface.

Therefore the current Coder/Executor choice is:

``` text
Qwen 3:8B
```

The abliterated Qwen remains available locally but is not currently
trusted for the primary OpenHands execution path.

------------------------------------------------------------------------

# 14. Proven End-to-End Execution

A real test has successfully demonstrated:

``` text
TaskGraph
    ↓
Orchestrator
    ↓
OpenHandsExecutor
    ↓
Qwen 3:8B
    ↓
OpenHands
    ↓
file_editor
    ↓
actual file
```

The model created:

``` text
FORGE_REAL_TASK_TEST.txt
```

and verified its contents.

This is the first major proof that Forge can execute a real internally
represented task against its actual workspace.

------------------------------------------------------------------------

# 15. Current Performance Findings

OpenHands executor initialization was measured at approximately:

``` text
0.01 seconds
```

Task execution was measured at:

``` text
~113 seconds
~149 seconds
~212 seconds
```

A complete real orchestration test reached approximately:

``` text
566 seconds
```

for a trivial task.

Therefore:

> OpenHands/Python initialization is not the primary performance
> bottleneck.

The main cost is local LLM inference plus repeated agent/tool
iterations.

------------------------------------------------------------------------

# 16. Ollama

Current Ollama version:

``` text
0.32.6
```

Installed local models observed during development:

``` text
huihui_ai/gemma-4-abliterated:12b
glm-5.2:cloud
llama2-uncensored:7b
huihui_ai/qwen3.5-abliterated:9b
deepseek-r1:8b
qwen3:8b
```

Current intended Forge roles:

``` text
DeepSeek R1 abliterated → Planner / Reviewer
Qwen 3:8B              → Coder / OpenHands execution
```

------------------------------------------------------------------------

# 17. GPU and Hardware Profile

## Laptop

``` text
Acer Nitro V 15
```

## CPU

Known information:

``` text
Intel Core i5
13th generation
```

The exact CPU SKU has not been established in the Forge logs and should
not be guessed.

## GPU

``` text
NVIDIA GeForce RTX 4050 Laptop GPU
```

Observed VRAM:

``` text
6141 MiB
≈ 6 GB
```

Observed GPU power capability:

``` text
75 W
```

Observed NVIDIA information:

``` text
NVIDIA-SMI 610.62
CUDA UMD 13.3
```

------------------------------------------------------------------------

# 18. Qwen GPU Utilization

Ollama reported:

``` text
qwen3:8b
SIZE: 6.0 GB
PROCESSOR: 30% CPU / 70% GPU
CONTEXT: 4096
```

An NVIDIA observation showed:

``` text
4454 MiB / 6141 MiB VRAM
GPU utilization: 39%
```

Other applications, including Brave, were also using GPU resources.

The 6 GB-class GPU means the Qwen runtime can be partially CPU-offloaded
because model/runtime/context overhead competes for VRAM.

------------------------------------------------------------------------

# 19. Model Loading Strategy

Aggressively unloading/loading models for every task was considered and
rejected.

Bad approach:

``` text
DeepSeek load
   ↓
plan
   ↓
unload
   ↓
Qwen load
   ↓
one task
   ↓
unload
   ↓
DeepSeek load
```

This would introduce unnecessary model-loading latency.

Preferred approach:

``` text
Planning phase:
DeepSeek stays warm

Coding phase:
Qwen stays warm

Review phase:
DeepSeek stays warm

Fix phase:
Qwen stays warm
```

Model lifecycle should therefore be **phase-based**, not task-based.

Ollama may also keep models resident after the Python client exits due
to its keep-alive behavior.

------------------------------------------------------------------------

# 20. Coder Reasoning Strategy

Because DeepSeek already produces architecture and task planning, Qwen
should not repeatedly re-plan the project.

Desired division:

``` text
DeepSeek:
What should we build?
Why?
What are the dependencies?
What architecture should we use?

Qwen:
Implement the approved task.

OpenHands:
Execute filesystem/terminal/tool operations.

CI:
Does it work?

Reviewer:
Is it actually correct?
```

The Coder system prompt should explicitly tell Qwen:

-   task specification is authoritative
-   do not redesign unrelated parts
-   implement the supplied task
-   inspect only relevant files
-   use tools directly
-   verify changes
-   run relevant tests
-   report blockers

This should reduce unnecessary reasoning and token generation.

------------------------------------------------------------------------

# 21. CI/CD Development Loop

The intended loop is:

``` text
PROJECT.md
    ↓
Planner
    ↓
Task Graph
    ↓
Coder
    ↓
OpenHands
    ↓
Code changes
    ↓
Tests / CI
    ↓
Application
    ↓
Designer / Reviewer
    ↓
review.md
    ↓
Corrective tasks
    ↓
Coder
    ↓
Tests / CI
    ↓
Reviewer
    ↓
repeat
```

A project should not be considered complete merely because Qwen says it
is complete.

Completion should require evidence.

------------------------------------------------------------------------

# 22. Completion Gate

Potential completion conditions:

``` text
All required tasks complete
        +
Tests pass
        +
Build passes
        +
Application starts
        +
Smoke tests pass
        +
Reviewer has no blocking findings
        |
        v
PROJECT COMPLETE
```

------------------------------------------------------------------------

# 23. Designer / Reviewer Browser and MCP

The Designer/Reviewer needs more than source-code access.

It should be able to:

-   start the application
-   navigate to the local application
-   interact with UI
-   inspect behavior
-   take screenshots
-   research documentation
-   research design patterns
-   compare results with design requirements
-   write research notes
-   create review findings

Architecture:

``` text
DeepSeek Reviewer
       |
       v
Browser MCP
       |
       +--> navigation
       +--> interaction
       +--> screenshot
       +--> inspection
       +--> research
```

The underlying browser should remain replaceable.

A lightweight browser is preferred because the project is intended to
run continuously alongside local LLM inference.

The exact browser/MCP backend has not yet been finalized.

------------------------------------------------------------------------

# 24. Visual Review Loop

For UI projects:

``` text
Qwen implements UI
       ↓
application starts
       ↓
browser opens local app
       ↓
screenshot
       ↓
DeepSeek Designer
       ↓
compare against design.md
       ↓
review.md
       ↓
corrective task
       ↓
Qwen
       ↓
CI
       ↓
new screenshot
       ↓
review again
```

The Reviewer therefore evaluates the **actual rendered result**, not
merely the source code.

------------------------------------------------------------------------

# 25. Research Capture

Designer research should become durable project knowledge.

Example:

``` text
forge/
└── research/
    ├── authentication-pattern.md
    ├── dashboard-layout.md
    └── api-design.md
```

Each research note should ideally contain:

-   question
-   source
-   finding
-   relevance
-   recommendation
-   adoption status
-   related task

This prevents repeated research.

------------------------------------------------------------------------

# 26. Event Bus

A major upcoming architecture component is a structured Forge event bus.

Possible events:

``` text
PROJECT_LOADED
PLANNER_STARTED
PLAN_CREATED
TASK_CREATED
TASK_STARTED
TASK_COMPLETED
TASK_FAILED
FILE_CREATED
FILE_MODIFIED
COMMAND_STARTED
COMMAND_FINISHED
TEST_STARTED
TEST_PASSED
TEST_FAILED
APPLICATION_STARTED
BROWSER_OPENED
SCREENSHOT_CAPTURED
RESEARCH_STARTED
RESEARCH_FOUND
REVIEW_STARTED
REVIEW_CREATED
FIX_REQUESTED
CI_STARTED
CI_PASSED
CI_FAILED
PROJECT_COMPLETED
```

The event system should become the source for the eventual dashboard.

------------------------------------------------------------------------

# 27. Why the Event Bus Matters

Without an event layer:

``` text
Agent does something
    ↓
terminal log
    ↓
information disappears
```

With an event layer:

``` text
Agent
  ↓
Forge Event Bus
  ↓
+-----------+-----------+-----------+
|           |           |           |
v           v           v
Dashboard  Event Log  Markdown
```

This enables:

-   live dashboard
-   history
-   debugging
-   recovery
-   audit trail
-   agent status
-   CI status
-   screenshot history
-   research history
-   task progress

------------------------------------------------------------------------

# 28. Final Four-Panel Dashboard

The desired final Forge interface should expose all major sides of the
system.

Conceptual layout:

``` text
┌─────────────────────────────────────────────────────────────────────┐
│                           FORGE                                    │
├──────────────────┬──────────────────────┬───────────────────────────┤
│                  │                      │                           │
│ MARKDOWN         │ PLANNER              │ CODER                     │
│                  │                      │                           │
│ PROJECT.md       │ DeepSeek R1          │ Qwen 3:8B                 │
│ plan.md          │                      │                           │
│ design.md        │ Architecture         │ Current task              │
│ review.md        │ Task graph           │ Current file              │
│ decisions.md     │ Decisions            │ Current tool               │
│ research/        │ Dependencies         │ Test status                │
│                  │                      │                           │
├──────────────────┴──────────────────────┴───────────────────────────┤
│                                                                     │
│                    RESOURCES / WORKSPACE                            │
│                                                                     │
│ File System | Research | Screenshots | Browser | CI | Logs         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

------------------------------------------------------------------------

# 29. Panel 1 --- Markdown / Knowledge

Displays:

``` text
PROJECT.md
plan.md
architecture.md
design.md
review.md
decisions.md
research/
```

The user can inspect what the agents are learning and deciding.

This keeps the system transparent.

------------------------------------------------------------------------

# 30. Panel 2 --- Planner

Shows DeepSeek's current state.

Example:

``` text
DEEPSEEK R1

Status:
Planning

Current:
Designing backend architecture

Tasks:
✓ Database
✓ Backend foundation
→ Authentication
○ Frontend
○ Integration
○ CI
```

It should also expose:

-   architecture decisions
-   task graph
-   dependencies
-   blocked tasks
-   planner outputs

------------------------------------------------------------------------

# 31. Panel 3 --- Coder

Shows Qwen's current work.

Example:

``` text
QWEN 3:8B

Status:
Implementing TASK-007

Task:
Authentication API

Current tool:
file_editor

Current file:
backend/auth/routes.py

Next:
Run tests

Tests:
18/18 passed
```

The UI should show meaningful tool activity rather than dumping every
raw token.

------------------------------------------------------------------------

# 32. Panel 4 --- Resources / Workspace

This panel shows the environment around the agents.

### File system

``` text
frontend/
backend/
tests/
docker/
forge/
```

### Research

``` text
FastAPI documentation
React reference
Dashboard design reference
```

### Screenshots

``` text
Initial UI
Reviewer screenshot
After fix
Final UI
```

### Browser

``` text
Current URL
Page title
Browser state
```

### CI

``` text
Tests: 42/42
Build: PASS
Lint: PASS
Integration: PASS
```

------------------------------------------------------------------------

# 33. Forge as a Project Observatory

The dashboard should let the user answer:

-   What is Forge doing?
-   Why is it doing it?
-   What did the Planner decide?
-   What is Qwen changing?
-   Which files changed?
-   What did the Reviewer find?
-   What research was performed?
-   What screenshots were captured?
-   Which tests passed?
-   What remains?

The dashboard is therefore an **observability layer**, not merely a chat
window.

------------------------------------------------------------------------

# 34. Failure Handling

Forge must expect failures.

Examples:

``` text
Ollama unavailable
Model connection failure
Tool call failure
PowerShell failure
Compilation failure
Test failure
Browser failure
MCP failure
Malformed planner output
Circular dependency
Reviewer rejection
```

Desired behavior:

``` text
failure
  ↓
classify
  ↓
retry if transient
  ↓
otherwise create actionable failure
  ↓
pause affected task
  ↓
show failure in dashboard
```

Forge should not silently mark a task successful when the implementation
did not actually complete.

------------------------------------------------------------------------

# 35. Ollama Health Management

Future model/runtime management should include:

-   Ollama health check
-   model availability check
-   model loaded/unloaded state
-   connection retries
-   transient error handling
-   model selection
-   keep-alive management
-   model status events

Example dashboard state:

``` text
OLLAMA

DeepSeek R1:
loaded

Qwen 3:8B:
loaded

VRAM:
4.4 / 6.1 GB
```

------------------------------------------------------------------------

# 36. Context Strategy

Forge should avoid sending the entire repository to the model for every
task.

Future task context should be:

``` text
Task
+
Relevant files
+
Relevant architecture
+
Relevant design decisions
+
Relevant review findings
+
Relevant tests
```

rather than:

``` text
Entire repository
+
Entire history
+
Every research document
```

This should reduce inference latency and improve agent focus.

------------------------------------------------------------------------

# 37. Future Project Knowledge / RAG

A future project knowledge index can include:

-   Markdown
-   source code
-   architecture
-   research
-   reviews
-   test results
-   decisions
-   previous agent outputs

Conceptually:

``` text
Project
   ↓
Indexer
   ↓
Knowledge Index
   ↓
Relevant Context
   ↓
Agent
```

This should be introduced after the fundamental autonomous loop is
stable.

------------------------------------------------------------------------

# 38. Security

Forge can execute commands, so execution boundaries matter.

Future controls should include:

-   workspace sandbox
-   command restrictions
-   filesystem boundaries
-   tool permissions
-   network policy
-   dangerous-command detection
-   confirmation policy
-   resource limits

The normal Coder workspace should be:

``` text
D:\AI\Projectsorge
```

------------------------------------------------------------------------

# 39. Agent Permission Model

Different agents should receive different capabilities.

  Agent      Files            Terminal      Browser      Research   Review
  ---------- ---------------- ------------- ------------ ---------- --------
  Planner    Project docs     Limited       Optional     Yes        No
  Coder      Read/write       Yes           No/limited   No         No
  Designer   Read project     Run/inspect   Yes          Yes        Yes
  CI         Test artifacts   Yes           No           No         No
  Reviewer   Read project     Run/inspect   Yes          Yes        Yes

The goal is to minimize unnecessary privileges.

------------------------------------------------------------------------

# 40. CI Architecture

Potential CI stages:

``` text
lint
format
unit tests
integration tests
type checking
build
application startup
health check
browser smoke test
visual review
```

Each stage should emit structured Forge events.

------------------------------------------------------------------------

# 41. Recovery and Persistence

Forge should eventually persist:

``` text
project ID
task graph
task states
current agent
current task
event log
review state
CI results
model configuration
```

If Forge stops:

``` text
Forge restart
    ↓
load state
    ↓
find incomplete work
    ↓
resume
```

OpenHands itself currently warns when no persistence directory is
provided and falls back to an in-memory event store. This should be
addressed when durable Forge sessions are implemented.

------------------------------------------------------------------------

# 42. Human Control

The system should remain controllable.

The user should eventually be able to:

``` text
pause
resume
cancel
retry
skip
approve
reject
edit PROJECT.md
edit design.md
edit plan.md
```

Human intervention should be visible in the event history.

------------------------------------------------------------------------

# 43. Current Development Environment

## Workspace

``` text
D:\AI\Projectsorge
```

## Python environments

Original environment:

``` text
.venv
Python 3.14.x
```

OpenHands environment:

``` text
.venv312
Python 3.12.13
```

OpenHands is currently installed in `.venv312`.

## OpenHands

``` text
1.42.1
```

## Pydantic

``` text
2.13.4
```

## Ollama

``` text
0.32.6
```

------------------------------------------------------------------------

# 44. Installed Model Inventory

Observed local Ollama inventory:

  ----------------------------------------------------------------------------------------
  Model                                                 Approx. size Current role
  ------------------------------------- ---------------------------- ---------------------
  `qwen3:8b`                                 \~5.2 GB model / \~6 GB Primary
                                                              loaded coder/executor

  `deepseek-r1:8b`                                          \~5.2 GB Planner/reviewer
                                                                     candidate

  `huihui_ai/qwen3.5-abliterated:9b`                        \~6.6 GB Tested; unreliable
                                                                     OpenHands tool
                                                                     calling

  `huihui_ai/gemma-4-abliterated:12b`                       \~7.6 GB Available

  `llama2-uncensored:7b`                                    \~3.8 GB Available

  `glm-5.2:cloud`                                              Cloud Available
  ----------------------------------------------------------------------------------------

The exact role of the other models is not currently part of the core
Forge architecture.

------------------------------------------------------------------------

# 45. Browser Resource Consideration

The machine has Brave installed and it appeared in GPU process listings
during testing.

However, Forge is intentionally not committing to Chrome as its
permanent browser backend.

The design requirement is:

> Use a browser/MCP implementation that is capable enough for agent
> research, interaction, and screenshots without unnecessarily consuming
> resources alongside local LLM inference.

The browser backend should therefore be replaceable.

------------------------------------------------------------------------

# 46. Testing Strategy

Forge follows a test-first approach.

Major components should have tests before being integrated.

Testing has covered:

``` text
Bootstrap
Project parser
Planner
Planner output validation
Task graph
DeepSeek planner
OpenHands SDK
OpenHands tool resolution
OpenHands executor
Real Orchestrator
```

A previous suite reached 31 tests before the real OpenHands integration
work was expanded.

The real OpenHands executor test successfully created and verified a
file.

The real orchestration test subsequently passed.

------------------------------------------------------------------------

# 47. Performance Optimization Roadmap

Current priority is reducing the cost of the agent loop.

Measure:

-   cold model load
-   warm model execution
-   tokens/second
-   number of LLM calls
-   prompt size
-   output size
-   tool-call count
-   tool execution time
-   test execution time

Then optimize:

1.  Coder prompt
2.  OpenHands iteration limits
3.  context size
4.  unnecessary reasoning
5.  redundant verification
6.  Ollama GPU/offload configuration
7.  CI batching
8.  project context retrieval

The goal is not necessarily 100% GPU utilization.

The goal is:

> **fast, reliable autonomous development iterations.**

------------------------------------------------------------------------

# 48. Why CI Should Be Batched

A major optimization principle is avoiding unnecessary validation after
every tiny change.

Instead of:

``` text
Task 1
 ↓
run entire CI

Task 2
 ↓
run entire CI

Task 3
 ↓
run entire CI
```

prefer:

``` text
Task 1
 ↓
Task 2
 ↓
Task 3
 ↓
relevant fast checks
 ↓
batch CI
```

The final CI gate still needs comprehensive validation.

This reduces repeated model/tool/test overhead.

------------------------------------------------------------------------

# 49. Final Conceptual Architecture

``` text
                           HUMAN
                             |
                             v
                         PROJECT.md
                             |
                             v
                   +-------------------+
                   | DeepSeek Planner   |
                   +-------------------+
                             |
                   plan.md / architecture.md
                             |
                             v
                         TaskGraph
                             |
                             v
                       Orchestrator
                             |
                +------------+------------+
                |                         |
                v                         v
          Qwen 3:8B                    CI/Test
                |
                v
          OpenHands SDK
          /     |               /      |               v       v        v
   FileEditor Terminal TaskTracker
         \       |       /
          \      |      /
           v     v     v
             Workspace
                 |
                 v
             Application
                 |
                 v
           Browser / MCP
                 |
        +--------+--------+
        |                 |
    Screenshots       Research
        |                 |
        +--------+--------+
                 |
                 v
        DeepSeek Designer
                 |
                 v
        design.md/review.md
                 |
                 v
          Corrective Tasks
                 |
                 v
             Qwen 3:8B
                 |
                 v
                CI
                 |
              repeat
```

------------------------------------------------------------------------

# 50. Final Product Vision

Forge should feel like supervising a local autonomous engineering team.

The user provides:

``` text
PROJECT.md
```

Forge then shows:

``` text
Planner:
Architecture complete.

Coder:
Implementing authentication.

Workspace:
backend/auth/routes.py modified.

CI:
18/18 tests passed.

Designer:
Dashboard spacing is inconsistent.

Research:
Found a better responsive layout pattern.

Coder:
Applying review changes.

CI:
42/42 tests passed.

Reviewer:
Approved.

Forge:
Project complete.
```

The user should always be able to see:

-   what the Planner decided
-   what the Coder is doing
-   what files are changing
-   what research was found
-   what screenshots were captured
-   what tests are running
-   what the Reviewer thinks
-   why the next task exists

------------------------------------------------------------------------

# 51. Core Principle

Forge is fundamentally a **closed autonomous development loop**:

``` text
PLAN
  ↓
IMPLEMENT
  ↓
EXECUTE
  ↓
TEST
  ↓
INSPECT
  ↓
RESEARCH
  ↓
REVIEW
  ↓
FIX
  ↓
TEST
  ↓
REVIEW
  ↓
REPEAT
```

The individual models are replaceable.

The important part is the system around them:

``` text
Markdown
+
Planner
+
TaskGraph
+
Orchestrator
+
OpenHands
+
Coder
+
Browser/MCP
+
Reviewer
+
CI
+
Event Bus
+
Dashboard
```

That combination is what turns local LLMs into a continuous
software-development system.
