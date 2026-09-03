from prsentinel.formatters.html import format_html
from prsentinel.models import Category, Finding, ReviewResult, Severity


def test_html_report_clean_result():
    result = ReviewResult(files_reviewed=2, provider="groq", model="x")
    html = format_html(result)
    assert "<html>" in html
    assert "No issues found" in html


def test_html_report_includes_findings_and_escapes_content():
    result = ReviewResult(
        findings=[
            Finding(
                "a.py",
                5,
                Severity.CRITICAL,
                Category.SECURITY,
                "Uses <script> unsafely",
                "Escape the input.",
            )
        ],
        files_reviewed=1,
        provider="groq",
        model="llama-3.3-70b-versatile",
    )
    html = format_html(result)
    assert "a.py" in html
    assert "&lt;script&gt;" in html
    assert "critical" in html.lower()
    assert "Escape the input." in html
