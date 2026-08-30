"""Parses unified diff text (the output of `git diff`) into structured files
and hunks, without pulling in a third party diff library.

The parser is intentionally forgiving. Real world diffs from different git
configurations vary slightly (rename headers, mode changes, binary markers),
so unrecognized lines are skipped rather than raising an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
FILE_HEADER_RE = re.compile(r"^diff --git a/(.*?) b/(.*?)$")


@dataclass
class DiffLine:
    """One line inside a hunk, with its position in the new file."""

    kind: str  # "add", "remove", or "context"
    content: str
    new_lineno: int | None


@dataclass
class DiffHunk:
    header: str
    lines: list[DiffLine] = field(default_factory=list)

    def to_text(self) -> str:
        rendered = [self.header]
        for line in self.lines:
            prefix = {"add": "+", "remove": "-", "context": " "}[line.kind]
            rendered.append(f"{prefix}{line.content}")
        return "\n".join(rendered)

    def added_line_count(self) -> int:
        return sum(1 for line in self.lines if line.kind == "add")


@dataclass
class DiffFile:
    path: str
    old_path: str | None = None
    is_binary: bool = False
    is_deleted: bool = False
    is_new: bool = False
    hunks: list[DiffHunk] = field(default_factory=list)

    def to_text(self) -> str:
        return "\n".join(hunk.to_text() for hunk in self.hunks)

    def total_changed_lines(self) -> int:
        return sum(
            1
            for hunk in self.hunks
            for line in hunk.lines
            if line.kind in ("add", "remove")
        )


def parse_unified_diff(diff_text: str) -> list[DiffFile]:
    """Parses raw unified diff text into a list of DiffFile objects.

    Files with no textual hunks (pure renames, mode changes, binary files)
    are still returned so callers can decide whether to skip them, but their
    `hunks` list will be empty.
    """

    files: list[DiffFile] = []
    current_file: DiffFile | None = None
    current_hunk: DiffHunk | None = None
    new_lineno = 0

    lines = diff_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        header_match = FILE_HEADER_RE.match(line)
        if header_match:
            if current_file is not None:
                files.append(current_file)
            old_path, new_path = header_match.group(1), header_match.group(2)
            current_file = DiffFile(path=new_path, old_path=old_path)
            current_hunk = None
            i += 1
            continue

        if current_file is None:
            i += 1
            continue

        if line.startswith("Binary files") or "GIT binary patch" in line:
            current_file.is_binary = True
            i += 1
            continue

        if line.startswith("deleted file mode"):
            current_file.is_deleted = True
            i += 1
            continue

        if line.startswith("new file mode"):
            current_file.is_new = True
            i += 1
            continue

        hunk_match = HUNK_HEADER_RE.match(line)
        if hunk_match:
            new_lineno = int(hunk_match.group(2))
            current_hunk = DiffHunk(header=line)
            current_file.hunks.append(current_hunk)
            i += 1
            continue

        if current_hunk is not None:
            if line.startswith("+") and not line.startswith("+++"):
                current_hunk.lines.append(
                    DiffLine("add", line[1:], new_lineno)
                )
                new_lineno += 1
            elif line.startswith("-") and not line.startswith("---"):
                current_hunk.lines.append(DiffLine("remove", line[1:], None))
            elif line.startswith(("---", "+++")):
                pass
            elif line.startswith("\\ No newline"):
                pass
            else:
                content = line[1:] if line.startswith(" ") else line
                current_hunk.lines.append(
                    DiffLine("context", content, new_lineno)
                )
                new_lineno += 1

        i += 1

    if current_file is not None:
        files.append(current_file)

    return files
