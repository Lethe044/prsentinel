from __future__ import annotations

from rich.console import Console
from rich.table import Table

from prsentinel.models import ReviewResult, Severity

SEVERITY_STYLE = {
    Severity.CRITICAL: "bold red",
    Severity.WARNING: "bold yellow",
    Severity.SUGGESTION: "cyan",
}

SEVERITY_ICON = {
    Severity.CRITICAL: "[x]",
    Severity.WARNING: "[!]",
    Severity.SUGGESTION: "[i]",
}


def print_review(result: ReviewResult, console: Console | None = None) -> None:
    console = console or Console()

    if not result.findings:
        console.print(
            f"\n[bold green]No issues found.[/bold green] "
            f"Reviewed {result.files_reviewed} file(s) with "
            f"{result.provider}/{result.model}.\n"
        )
        if result.chunks_failed:
            console.print(
                f"[yellow]Note:[/yellow] {result.chunks_failed} chunk(s) "
                "failed to review and were skipped."
            )
        return

    ordered = sorted(result.findings, key=lambda f: (-f.severity.rank, f.file, f.line or 0))

    table = Table(show_header=True, header_style="bold", expand=True)
    table.add_column("Severity", width=10)
    table.add_column("File", overflow="fold")
    table.add_column("Line", width=6, justify="right")
    table.add_column("Category", width=15)
    table.add_column("Message", overflow="fold")

    for finding in ordered:
        style = SEVERITY_STYLE.get(finding.severity, "")
        icon = SEVERITY_ICON.get(finding.severity, "")
        message = finding.message
        if finding.suggestion:
            message += f"\n[dim]Suggestion: {finding.suggestion}[/dim]"
        table.add_row(
            f"[{style}]{icon} {finding.severity.value}[/{style}]",
            finding.file,
            str(finding.line) if finding.line is not None else "-",
            finding.category.value,
            message,
        )

    console.print(table)

    counts = result.counts_by_severity()
    summary = (
        f"\n{len(result.findings)} finding(s) across {result.files_reviewed} "
        f"file(s): {counts['critical']} critical, {counts['warning']} warning, "
        f"{counts['suggestion']} suggestion."
    )
    console.print(summary)

    if result.chunks_failed:
        console.print(
            f"[yellow]Note:[/yellow] {result.chunks_failed} chunk(s) failed "
            "to review and were skipped."
        )
