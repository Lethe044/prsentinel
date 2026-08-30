"""Exports findings as SARIF 2.1.0, so they can be uploaded with
github/codeql-action/upload-sarif and show up in the GitHub Security tab
alongside other code scanning results.
"""

from __future__ import annotations

from prsentinel import __version__
from prsentinel.models import ReviewResult, Severity

SARIF_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.WARNING: "warning",
    Severity.SUGGESTION: "note",
}


def format_sarif(result: ReviewResult) -> dict:
    rules = {}
    findings_json = []

    for finding in result.findings:
        rule_id = f"prsentinel/{finding.category.value}"
        rules.setdefault(
            rule_id,
            {
                "id": rule_id,
                "name": finding.category.value,
                "shortDescription": {"text": f"PR Sentinel: {finding.category.value} finding"},
            },
        )

        region = {"startLine": finding.line} if finding.line else {"startLine": 1}
        findings_json.append(
            {
                "ruleId": rule_id,
                "level": SARIF_LEVEL[finding.severity],
                "message": {"text": finding.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": finding.file},
                            "region": region,
                        }
                    }
                ],
            }
        )

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "PR Sentinel",
                        "informationUri": "https://github.com/Lethe044/prsentinel",
                        "version": __version__,
                        "rules": list(rules.values()),
                    }
                },
                "results": findings_json,
            }
        ],
    }
