from dataclasses import dataclass, field


@dataclass
class Finding:
    summary: str
    blocking: bool = True


@dataclass
class ReviewResult:
    approved: bool
    findings: list[Finding] = field(default_factory=list)
    notes: str = ""
