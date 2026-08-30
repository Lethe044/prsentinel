from prsentinel.formatters.json_formatter import format_json
from prsentinel.formatters.markdown import MARKER, format_inline_comments, format_summary_comment
from prsentinel.formatters.sarif import format_sarif
from prsentinel.models import Category, Finding, ReviewResult, Severity


def sample_result() -> ReviewResult:
    return ReviewResult(
        findings=[
            Finding("a.py", 5, Severity.CRITICAL, Category.SECURITY, "SQL injection risk", "Use parameterized queries."),
            Finding("b.py", None, Severity.SUGGESTION, Category.STYLE, "Consider a docstring."),
        ],
        files_reviewed=2,
        provider="groq",
        model="llama-3.3-70b-versatile",
    )


def test_summary_comment_contains_marker_and_findings():
    body = format_summary_comment(sample_result())
    assert MARKER in body
    assert "SQL injection risk" in body
    assert "a.py" in body
    assert "b.py" in body


def test_summary_comment_clean_result():
    body = format_summary_comment(ReviewResult(files_reviewed=3, provider="groq", model="x"))
    assert "No issues found" in body


def test_inline_comments_skip_findings_without_a_line():
    comments = format_inline_comments(sample_result())
    assert len(comments) == 1
    assert comments[0]["path"] == "a.py"
    assert comments[0]["line"] == 5


def test_json_formatter_shape():
    data = format_json(sample_result())
    assert data["provider"] == "groq"
    assert data["counts"]["critical"] == 1
    assert len(data["findings"]) == 2


def test_sarif_formatter_shape():
    sarif = format_sarif(sample_result())
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "PR Sentinel"
    assert len(run["results"]) == 2
    levels = {r["level"] for r in run["results"]}
    assert "error" in levels
    assert "note" in levels
