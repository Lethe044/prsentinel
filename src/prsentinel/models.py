"""Core data structures shared across the codebase."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    """How serious a finding is, ordered from least to most severe."""

    SUGGESTION = "suggestion"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        order = {
            Severity.SUGGESTION: 0,
            Severity.WARNING: 1,
            Severity.CRITICAL: 2,
        }
        return order[self]

    @classmethod
    def from_str(cls, value: str) -> "Severity":
        value = (value or "").strip().lower()
        for member in cls:
            if member.value == value:
                return member
        # Unknown severities from a model response are treated as warnings
        # instead of being dropped, so nothing gets silently lost.
        return cls.WARNING


class Category(str, Enum):
    """What kind of problem a finding describes."""

    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    TEST = "test"
    MAINTAINABILITY = "maintainability"
    OTHER = "other"

    @classmethod
    def from_str(cls, value: str) -> "Category":
        value = (value or "").strip().lower()
        for member in cls:
            if member.value == value:
                return member
        return cls.OTHER


@dataclass
class Finding:
    """A single issue spotted in a reviewed diff."""

    file: str
    line: Optional[int]
    severity: Severity
    category: Category
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ChunkResult:
    """The raw outcome of reviewing a single diff chunk."""

    file: str
    findings: list[Finding] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ReviewResult:
    """The aggregated outcome of an entire review run."""

    findings: list[Finding] = field(default_factory=list)
    files_reviewed: int = 0
    files_skipped: int = 0
    chunks_failed: int = 0
    provider: str = ""
    model: str = ""

    def findings_at_or_above(self, minimum: Severity) -> list[Finding]:
        return [f for f in self.findings if f.severity.rank >= minimum.rank]

    def highest_severity(self) -> Optional[Severity]:
        if not self.findings:
            return None
        return max(self.findings, key=lambda f: f.severity.rank).severity

    def counts_by_severity(self) -> dict:
        counts = {s.value: 0 for s in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts
