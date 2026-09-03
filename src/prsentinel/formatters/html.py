"""Renders a review result as a single, dependency-free HTML file. Useful
as a CI artifact you can download and open, or for archiving a review
outside of GitHub or GitLab entirely.
"""

from __future__ import annotations

from html import escape

from prsentinel.models import ReviewResult, Severity

SEVERITY_COLOR = {
    Severity.CRITICAL: "#dc2626",
    Severity.WARNING: "#d97706",
    Severity.SUGGESTION: "#2563eb",
}

STYLE = """
body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif;
       max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1f2937; }
h1 { font-size: 22px; }
.meta { color: #6b7280; margin-bottom: 24px; }
.counts { display: flex; gap: 16px; margin-bottom: 24px; }
.count-box { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; }
.count-box .n { font-size: 20px; font-weight: 700; }
.file-group { margin-bottom: 24px; }
.file-group h2 { font-size: 15px; font-family: monospace;
                  background: #f3f4f6; padding: 6px 10px; border-radius: 6px; }
.finding { border-left: 4px solid #e5e7eb; padding: 8px 14px; margin: 8px 0; }
.finding .label { font-weight: 700; font-size: 12px; text-transform: uppercase; }
.finding .location { color: #6b7280; font-size: 12px; }
.finding .suggestion { color: #374151; font-size: 13px; margin-top: 4px; }
.clean { color: #059669; font-weight: 600; }
"""


def format_html(result: ReviewResult) -> str:
    counts = result.counts_by_severity()

    parts = [
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">",
        "<title>PR Sentinel review</title>",
        f"<style>{STYLE}</style></head><body>",
        "<h1>PR Sentinel review</h1>",
        f"<div class=\"meta\">Reviewed {result.files_reviewed} file(s) with "
        f"{escape(result.provider)}/{escape(result.model)}</div>",
        "<div class=\"counts\">",
        f"<div class=\"count-box\"><div class=\"n\">{counts['critical']}</div>Critical</div>",
        f"<div class=\"count-box\"><div class=\"n\">{counts['warning']}</div>Warning</div>",
        f"<div class=\"count-box\"><div class=\"n\">{counts['suggestion']}</div>Suggestion</div>",
        "</div>",
    ]

    if not result.findings:
        parts.append("<p class=\"clean\">No issues found.</p>")
    else:
        by_file: dict[str, list] = {}
        for finding in result.findings:
            by_file.setdefault(finding.file, []).append(finding)

        for file_path, findings in by_file.items():
            parts.append(f"<div class=\"file-group\"><h2>{escape(file_path)}</h2>")
            for finding in sorted(findings, key=lambda f: -f.severity.rank):
                color = SEVERITY_COLOR[finding.severity]
                location = f"line {finding.line}" if finding.line is not None else "general"
                parts.append(f"<div class=\"finding\" style=\"border-left-color:{color}\">")
                parts.append(
                    f"<div class=\"label\" style=\"color:{color}\">"
                    f"{escape(finding.severity.value)}</div>"
                )
                parts.append(
                    f"<div class=\"location\">{escape(location)} - "
                    f"{escape(finding.category.value)}</div>"
                )
                parts.append(f"<div>{escape(finding.message)}</div>")
                if finding.suggestion:
                    parts.append(
                        f"<div class=\"suggestion\">Suggested fix: "
                        f"{escape(finding.suggestion)}</div>"
                    )
                parts.append("</div>")
            parts.append("</div>")

    parts.append("</body></html>")
    return "".join(parts)
