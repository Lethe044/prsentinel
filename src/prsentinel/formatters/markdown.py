from __future__ import annotations

from prsentinel.models import Finding, ReviewResult, Severity

SEVERITY_LABEL = {
    Severity.CRITICAL: "Critical",
    Severity.WARNING: "Warning",
    Severity.SUGGESTION: "Suggestion",
}

MARKER = "<!-- prsentinel-summary -->"


def format_summary_comment(result: ReviewResult, show_footer: bool = True) -> str:
    """Builds the single summary comment posted (and later updated) on a
    pull request or merge request. The MARKER lets PR Sentinel find and
    edit its own previous comment instead of piling up duplicates on every
    push.
    """

    lines = [MARKER, "## PR Sentinel review", ""]

    counts = result.counts_by_severity()
    lines.append(
        f"Reviewed {result.files_reviewed} file(s) with "
        f"`{result.provider}/{result.model}`."
    )
    lines.append("")
    lines.append(
        f"| Critical | Warning | Suggestion |\n|---|---|---|\n"
        f"| {counts['critical']} | {counts['warning']} | {counts['suggestion']} |"
    )
    lines.append("")

    if not result.findings:
        lines.append("No issues found in the changed lines. Nice work.")
        if show_footer:
            lines.append(_footer())
        return "\n".join(lines)

    by_file: dict[str, list[Finding]] = {}
    for finding in result.findings:
        by_file.setdefault(finding.file, []).append(finding)

    for file_path, findings in by_file.items():
        lines.append(f"### `{file_path}`")
        for finding in sorted(findings, key=lambda f: -f.severity.rank):
            location = f"line {finding.line}" if finding.line is not None else "general"
            label = SEVERITY_LABEL[finding.severity]
            lines.append(f"- **{label}** ({location}, {finding.category.value}): {finding.message}")
            if finding.suggestion:
                lines.append(f"  - Suggested fix: {finding.suggestion}")
        lines.append("")

    if result.chunks_failed:
        lines.append(
            f"_{result.chunks_failed} chunk(s) could not be reviewed and "
            "were skipped, likely due to a provider error or rate limit._"
        )

    if show_footer:
        lines.append(_footer())

    return "\n".join(lines)


def _footer() -> str:
    return (
        "\n---\n"
        "*Reviewed by [PR Sentinel](https://github.com/Lethe044/prsentinel), "
        "a free, self-hosted AI code reviewer. "
        "[Report an issue](https://github.com/Lethe044/prsentinel/issues) "
        "if a finding looks wrong.*"
    )


def format_inline_comments(result: ReviewResult) -> list[dict]:
    """Builds the list of inline review comments in the shape expected by
    the GitHub pulls review API (path, line, body).
    """

    comments = []
    for finding in result.findings:
        if finding.line is None:
            continue
        label = SEVERITY_LABEL[finding.severity]
        body = f"**{label}** ({finding.category.value}): {finding.message}"
        if finding.suggestion:
            body += f"\n\nSuggested fix: {finding.suggestion}"
        comments.append({"path": finding.file, "line": finding.line, "body": body})
    return comments
