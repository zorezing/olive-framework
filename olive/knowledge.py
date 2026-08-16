import json
from datetime import datetime, timezone
from pathlib import Path

from olive.events import Event, EventBus, EventType
from olive.state.review import ReviewResult


class KnowledgeStore:
    """Writes durable, human-readable project knowledge into --state-dir
    as a run progresses: plan.md (the task graph, regenerated each time
    planning completes), decisions.md (an append-only log of notable
    choices -- which planner/executor/reviewer/models were used, gate
    outcomes), and reviews/review-NNN.md + .json (one snapshot per
    review, not overwritten, so review history accumulates across runs).

    Piggybacks on --state-dir rather than inventing a second directory
    convention: if you don't want persisted state, you also don't get
    accumulated docs, which is a consistent, single opt-in.

    This intentionally does not attempt architecture.md/design.md/
    research/ from the original spec layout -- there's no agent in this
    codebase that produces architecture decisions or research findings
    independent of the plan/review content already captured here, and
    fabricating empty placeholder files for capabilities that don't
    exist would be worse than not having them.
    """

    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.plan_path = self.state_dir / "plan.md"
        self.decisions_path = self.state_dir / "decisions.md"
        self.reviews_dir = self.state_dir / "reviews"

        self._project_name = ""
        self._goal = ""
        self._planner_name = ""
        self._tasks: list[dict] = []
        self._review_count = 0

    def attach(self, events: EventBus) -> None:
        events.subscribe(self._on_event)

    def _on_event(self, event: Event) -> None:
        if event.type == EventType.PROJECT_LOADED:
            self._project_name = event.payload.get("name", "")
            self._goal = event.payload.get("goal", "")

        elif event.type == EventType.PLANNER_STARTED:
            self._planner_name = event.payload.get("planner", "")

        elif event.type == EventType.TASK_CREATED:
            self._tasks.append(dict(event.payload))

        elif event.type == EventType.PLAN_CREATED:
            self._write_plan()

    def record_decision(self, summary: str) -> None:
        """Append a timestamped line to decisions.md. Called explicitly
        by the CLI at meaningful points (model/agent choices, gate
        outcomes) rather than inferred from generic events, so the log
        reads as plain, specific sentences.
        """

        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        line = f"- {timestamp} -- {summary}\n"

        with self.decisions_path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def record_review(self, result: ReviewResult, reviewer_name: str) -> None:
        """Write a numbered review-NNN.md/.json snapshot. Works uniformly
        for every Reviewer implementation, since it's built from the
        ReviewResult object rather than depending on a reviewer having
        written its own review.json to the workspace (SimpleReviewer
        never does).
        """

        self.reviews_dir.mkdir(parents=True, exist_ok=True)
        self._review_count += 1
        n = self._review_count

        payload = {
            "reviewer": reviewer_name,
            "approved": result.approved,
            "findings": [
                {"summary": f.summary, "blocking": f.blocking}
                for f in result.findings
            ],
            "notes": result.notes,
        }
        (self.reviews_dir / f"review-{n:03}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

        lines = [
            f"# Review {n:03} ({reviewer_name})",
            "",
            f"**Verdict:** {'APPROVED' if result.approved else 'CHANGES REQUESTED'}",
            "",
        ]
        if result.notes:
            lines += [result.notes, ""]
        if result.findings:
            lines.append("## Findings")
            lines.append("")
            for f in result.findings:
                tag = "BLOCKING" if f.blocking else "note"
                lines.append(f"- [{tag}] {f.summary}")
        (self.reviews_dir / f"review-{n:03}.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def _write_plan(self) -> None:
        lines = [
            f"# Plan: {self._project_name or '(unnamed project)'}",
            "",
        ]
        if self._goal:
            lines += [f"**Goal:** {self._goal}", ""]
        lines += [f"**Planner:** {self._planner_name or 'n/a'}", ""]
        lines.append("## Tasks")
        lines.append("")

        for task in self._tasks:
            deps = ", ".join(task.get("dependencies", [])) or "none"
            lines.append(
                f"- **{task.get('task_id', '?')}**: "
                f"{task.get('title', '')} (depends on: {deps})"
            )

        self.plan_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
