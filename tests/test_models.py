from prsentinel.models import Category, Finding, ReviewResult, Severity


def test_severity_ranking_orders_critical_highest():
    assert Severity.CRITICAL.rank > Severity.WARNING.rank > Severity.SUGGESTION.rank


def test_severity_from_str_unknown_defaults_to_warning():
    assert Severity.from_str("apocalyptic") == Severity.WARNING


def test_severity_from_str_known_values():
    assert Severity.from_str("critical") == Severity.CRITICAL
    assert Severity.from_str("SUGGESTION") == Severity.SUGGESTION


def test_category_from_str_unknown_defaults_to_other():
    assert Category.from_str("nonsense") == Category.OTHER


def make_result() -> ReviewResult:
    return ReviewResult(
        findings=[
            Finding("a.py", 1, Severity.SUGGESTION, Category.STYLE, "minor"),
            Finding("a.py", 2, Severity.CRITICAL, Category.SECURITY, "sql injection"),
            Finding("b.py", None, Severity.WARNING, Category.BUG, "off by one"),
        ],
        files_reviewed=2,
    )


def test_findings_at_or_above_filters_correctly():
    result = make_result()
    critical_only = result.findings_at_or_above(Severity.CRITICAL)
    assert len(critical_only) == 1
    assert critical_only[0].message == "sql injection"


def test_highest_severity():
    result = make_result()
    assert result.highest_severity() == Severity.CRITICAL


def test_highest_severity_none_when_empty():
    assert ReviewResult().highest_severity() is None


def test_counts_by_severity():
    result = make_result()
    counts = result.counts_by_severity()
    assert counts["critical"] == 1
    assert counts["warning"] == 1
    assert counts["suggestion"] == 1
