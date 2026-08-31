import json
import threading

from prsentinel.config import Config
from prsentinel.models import Severity
from prsentinel.providers.base import BaseProvider
from prsentinel.reviewer import _extract_json, run_review

SAMPLE_DIFF = """\
diff --git a/app/utils.py b/app/utils.py
index 1a2b3c4..5d6e7f8 100644
--- a/app/utils.py
+++ b/app/utils.py
@@ -10,3 +10,4 @@ def divide(a, b):
     return a / b
+def get_user(user_id):
+    return db.query(f"SELECT * FROM users WHERE id = {user_id}")
"""


class FakeProvider(BaseProvider):
    name = "fake"
    default_model = "fake-model"

    def __init__(self, response_text: str, **kwargs):
        super().__init__(**kwargs)
        self.response_text = response_text
        self.calls = 0
        self._lock = threading.Lock()

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        with self._lock:
            self.calls += 1
        return self.response_text


def test_extract_json_handles_plain_json():
    data = _extract_json('{"findings": []}')
    assert data == {"findings": []}


def test_extract_json_handles_markdown_fence():
    raw = '```json\n{"findings": [{"message": "x"}]}\n```'
    data = _extract_json(raw)
    assert data["findings"][0]["message"] == "x"


def test_run_review_finds_a_critical_sql_injection(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = json.dumps(
        {
            "findings": [
                {
                    "line": 12,
                    "severity": "critical",
                    "category": "security",
                    "message": "Raw SQL string formatting allows injection.",
                    "suggestion": "Use parameterized queries.",
                }
            ]
        }
    )
    provider = FakeProvider(response)
    config = Config(cache_enabled=False)

    result = run_review(SAMPLE_DIFF, config, provider)

    assert result.files_reviewed == 1
    assert len(result.findings) == 1
    assert result.findings[0].severity == Severity.CRITICAL
    assert "injection" in result.findings[0].message.lower()


def test_run_review_skips_ignored_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    diff_with_lockfile = SAMPLE_DIFF + (
        "\ndiff --git a/package-lock.json b/package-lock.json\n"
        "index 111..222 100644\n"
        "--- a/package-lock.json\n"
        "+++ b/package-lock.json\n"
        "@@ -1,1 +1,1 @@\n"
        "-{}\n"
        "+{ }\n"
    )
    provider = FakeProvider(json.dumps({"findings": []}))
    config = Config(cache_enabled=False)

    result = run_review(diff_with_lockfile, config, provider)

    assert result.files_reviewed == 1
    assert result.files_skipped == 1


def test_run_review_uses_cache_on_second_call(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    provider = FakeProvider(json.dumps({"findings": []}))
    config = Config(cache_enabled=True)

    run_review(SAMPLE_DIFF, config, provider)
    run_review(SAMPLE_DIFF, config, provider)

    assert provider.calls == 1


def test_run_review_applies_severity_threshold(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = json.dumps(
        {
            "findings": [
                {"line": 11, "severity": "suggestion", "category": "style", "message": "minor"},
                {"line": 12, "severity": "critical", "category": "security", "message": "major"},
            ]
        }
    )
    provider = FakeProvider(response)
    config = Config(cache_enabled=False, severity_threshold="critical")

    result = run_review(SAMPLE_DIFF, config, provider)

    assert len(result.findings) == 1
    assert result.findings[0].message == "major"


def test_run_review_handles_provider_error_gracefully(tmp_path, monkeypatch):
    from prsentinel.providers.base import ProviderError

    monkeypatch.chdir(tmp_path)

    class BrokenProvider(FakeProvider):
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            raise ProviderError("simulated outage")

    provider = BrokenProvider("unused")
    config = Config(cache_enabled=False)

    result = run_review(SAMPLE_DIFF, config, provider)

    assert result.chunks_failed == 1
    assert result.findings == []


def test_run_review_handles_multiple_files_concurrently(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    two_file_diff = SAMPLE_DIFF + (
        "\ndiff --git a/app/other.py b/app/other.py\n"
        "index 111..222 100644\n"
        "--- a/app/other.py\n"
        "+++ b/app/other.py\n"
        "@@ -1,1 +1,2 @@\n"
        " def existing():\n"
        "+    pass\n"
    )
    response = json.dumps({"findings": []})
    provider = FakeProvider(response)
    config = Config(cache_enabled=False, max_workers=4)

    result = run_review(two_file_diff, config, provider)

    assert result.files_reviewed == 2
    assert provider.calls == 2


def test_run_review_respects_max_workers_of_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = json.dumps({"findings": []})
    provider = FakeProvider(response)
    config = Config(cache_enabled=False, max_workers=1)

    result = run_review(SAMPLE_DIFF, config, provider)

    assert result.files_reviewed == 1
