"""Lets people silence a specific finding the same way they would silence a
linter: a comment near the line in question. This works across languages
by matching a plain marker string rather than any particular comment
syntax, since the marker is unambiguous on its own.

Supported markers, placed anywhere in a line (any comment style works,
since only the marker text itself is matched):

    prsentinel-ignore-line          suppresses findings on this exact line
    prsentinel-ignore-next-line     suppresses findings on the following line
    prsentinel-ignore-file          suppresses every finding in this file
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prsentinel.diffparser import DiffFile

IGNORE_FILE_MARKER = "prsentinel-ignore-file"
IGNORE_LINE_MARKER = "prsentinel-ignore-line"
IGNORE_NEXT_LINE_MARKER = "prsentinel-ignore-next-line"


@dataclass
class FileSuppressions:
    file_suppressed: bool = False
    suppressed_lines: set[int] = field(default_factory=set)

    def covers(self, line: int | None) -> bool:
        if self.file_suppressed:
            return True
        if line is None:
            return False
        return line in self.suppressed_lines


def build_suppressions(diff_file: DiffFile) -> FileSuppressions:
    suppressions = FileSuppressions()
    pending_next_line = False

    for hunk in diff_file.hunks:
        for line in hunk.lines:
            if line.kind == "remove":
                continue

            content = line.content

            if IGNORE_FILE_MARKER in content:
                suppressions.file_suppressed = True

            if pending_next_line and line.new_lineno is not None:
                suppressions.suppressed_lines.add(line.new_lineno)
                pending_next_line = False

            if IGNORE_LINE_MARKER in content and line.new_lineno is not None:
                suppressions.suppressed_lines.add(line.new_lineno)

            if IGNORE_NEXT_LINE_MARKER in content:
                pending_next_line = True

    return suppressions


def build_suppressions_by_file(diff_files: list[DiffFile]) -> dict[str, FileSuppressions]:
    return {diff_file.path: build_suppressions(diff_file) for diff_file in diff_files}
