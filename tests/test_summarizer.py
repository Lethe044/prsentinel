import json

import pytest

from prsentinel.providers.base import BaseProvider, ProviderError
from prsentinel.summarizer import MAX_DIFF_CHARS, summarize_diff

SAMPLE_DIFF = """\
diff --git a/app/auth.py b/app/auth.py
index 111..222 100644
--- a/app/auth.py
+++ b/app/auth.py
@@ -1,2 +1,4 @@
+def login(user, password):
+    return check_credentials(user, password)
"""


class FakeProvider(BaseProvider):
    name = "fake"
    default_model = "fake-model"

    def __init__(self, response_text: str, **kwargs):
        super().__init__(**kwargs)
        self.response_text = response_text
        self.last_user_prompt = None

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.last_user_prompt = user_prompt
        return self.response_text


def test_summarize_diff_returns_parsed_summary():
    response = json.dumps(
        {
            "title": "feat: add login endpoint",
            "summary": "Adds a basic login function that checks credentials.",
            "highlights": ["New login() function"],
        }
    )
    provider = FakeProvider(response)

    summary = summarize_diff(SAMPLE_DIFF, provider)

    assert summary.title == "feat: add login endpoint"
    assert "login" in summary.summary.lower()
    assert summary.highlights == ["New login() function"]


def test_summarize_diff_handles_markdown_fence():
    response = '```json\n{"title": "fix: bug", "summary": "Fixes a bug.", "highlights": []}\n```'
    provider = FakeProvider(response)

    summary = summarize_diff(SAMPLE_DIFF, provider)

    assert summary.title == "fix: bug"


def test_summarize_diff_raises_provider_error_on_bad_json():
    provider = FakeProvider("not json at all")
    with pytest.raises(ProviderError):
        summarize_diff(SAMPLE_DIFF, provider)


def test_summarize_diff_truncates_very_large_diffs():
    huge_diff = SAMPLE_DIFF + ("+x = 1\n" * (MAX_DIFF_CHARS))
    response = json.dumps({"title": "chore: big change", "summary": "Big.", "highlights": []})
    provider = FakeProvider(response)

    summarize_diff(huge_diff, provider)

    assert len(provider.last_user_prompt) < len(huge_diff)
    assert "truncated" in provider.last_user_prompt.lower()
