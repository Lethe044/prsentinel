"""Builds the prompt sent to the language model for each diff chunk.

The prompt asks for strict JSON so responses can be parsed reliably across
very different model providers and sizes, from a small local Ollama model
to a large hosted one.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are an experienced senior software engineer performing a \
pull request code review. You review only the lines that were added or \
changed in the diff you are given, using surrounding context lines only to \
understand intent.

Focus on things that actually matter in a real review: bugs, security \
issues, broken edge cases, resource leaks, performance problems, missing or \
weak error handling, and missing tests for meaningfully changed logic. Do \
not comment on personal style preferences unless they violate a rule the \
user explicitly gives you. Do not invent problems that are not actually in \
the diff. If the change looks fine, return an empty findings list rather \
than manufacturing feedback.

You must respond with a single JSON object and nothing else. No markdown \
code fences, no commentary before or after it. The JSON shape is exactly:

{
  "findings": [
    {
      "line": <integer line number in the new file, or null if it applies \
to the whole file>,
      "severity": "suggestion" | "warning" | "critical",
      "category": "bug" | "security" | "performance" | "style" | "test" | \
"maintainability" | "other",
      "message": "<one or two sentence explanation>",
      "suggestion": "<short concrete fix, or null if not applicable>"
    }
  ]
}
"""


def build_user_prompt(
    file_path: str,
    diff_chunk_text: str,
    custom_rules: list[str],
    language_hints: bool,
) -> str:
    sections = [f"File: {file_path}", "", "Diff:", "```diff", diff_chunk_text, "```"]

    if language_hints:
        sections.append(
            "\nConsider idioms and common pitfalls specific to the "
            "language this file is written in, based on its extension "
            "and content."
        )

    if custom_rules:
        rules_text = "\n".join(f"- {rule}" for rule in custom_rules)
        sections.append(
            "\nIn addition to a general review, also check against these "
            f"project specific rules:\n{rules_text}"
        )

    return "\n".join(sections)
