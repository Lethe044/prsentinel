"""Suggests a pull request title and description from a diff.

This is a separate, smaller feature from the line-by-line code review: it
answers "what did this change do and why", which is useful even for
someone who does not want automated review comments but is tired of
writing PR descriptions by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prsentinel.prompts import SUMMARIZE_SYSTEM_PROMPT, build_summarize_prompt
from prsentinel.providers.base import BaseProvider, ProviderError
from prsentinel.reviewer import _extract_json

MAX_DIFF_CHARS = 24000


@dataclass
class Summary:
    title: str
    summary: str
    highlights: list[str] = field(default_factory=list)


def summarize_diff(diff_text: str, provider: BaseProvider) -> Summary:
    truncated = diff_text
    was_truncated = False
    if len(diff_text) > MAX_DIFF_CHARS:
        truncated = diff_text[:MAX_DIFF_CHARS]
        was_truncated = True

    user_prompt = build_summarize_prompt(truncated)
    if was_truncated:
        user_prompt += (
            "\n\nNote: this diff was truncated because it is very large. "
            "Base the summary on what is shown."
        )

    raw_response = provider.complete(SUMMARIZE_SYSTEM_PROMPT, user_prompt)

    try:
        data = _extract_json(raw_response)
    except ValueError as exc:
        raise ProviderError(
            "The model's response could not be parsed as JSON while "
            "generating a summary."
        ) from exc

    return Summary(
        title=(data.get("title") or "").strip(),
        summary=(data.get("summary") or "").strip(),
        highlights=[h for h in (data.get("highlights") or []) if h],
    )
