"""Orchestrates a full review run: parsing the diff, filtering ignored
files, chunking large hunks, calling the provider, and turning its raw text
responses into structured Finding objects.
"""

from __future__ import annotations

import json
import re
from typing import Callable, Optional

from prsentinel import cache
from prsentinel.config import Config
from prsentinel.diffparser import DiffFile, DiffHunk, parse_unified_diff
from prsentinel.ignore import is_ignored
from prsentinel.models import Category, ChunkResult, Finding, ReviewResult, Severity
from prsentinel.prompts import SYSTEM_PROMPT, build_user_prompt
from prsentinel.providers.base import BaseProvider, ProviderError

JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

ProgressCallback = Callable[[str], None]


def _extract_json(raw_text: str) -> dict:
    """Model responses are usually clean JSON, but some models wrap it in a
    markdown code fence anyway despite instructions. This handles both.
    """

    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = JSON_BLOCK_RE.search(text)
        if match:
            return json.loads(match.group(0))
        raise


def _chunk_hunks(hunks: list[DiffHunk], max_lines: int) -> list[list[DiffHunk]]:
    """Groups hunks together up to max_lines per chunk, so a single very
    large file does not blow past a model's context window or a free tier
    token budget in one request.
    """

    chunks: list[list[DiffHunk]] = []
    current: list[DiffHunk] = []
    current_lines = 0

    for hunk in hunks:
        hunk_lines = len(hunk.lines)
        if current and current_lines + hunk_lines > max_lines:
            chunks.append(current)
            current = []
            current_lines = 0
        current.append(hunk)
        current_lines += hunk_lines

    if current:
        chunks.append(current)

    return chunks


def review_chunk(
    provider: BaseProvider,
    file_path: str,
    chunk_text: str,
    custom_rules: list[str],
    language_hints: bool,
    use_cache: bool,
) -> ChunkResult:
    user_prompt = build_user_prompt(file_path, chunk_text, custom_rules, language_hints)

    cache_key = None
    if use_cache:
        cache_key = cache.make_key(chunk_text, provider.name, provider.model)
        cached = cache.get(cache_key)
        if cached is not None:
            return _parse_response(file_path, cached)

    try:
        raw_response = provider.complete(SYSTEM_PROMPT, user_prompt)
    except ProviderError as exc:
        return ChunkResult(file=file_path, error=str(exc))

    if use_cache and cache_key:
        cache.set(cache_key, raw_response)

    return _parse_response(file_path, raw_response)


def _parse_response(file_path: str, raw_response: str) -> ChunkResult:
    try:
        data = _extract_json(raw_response)
    except (json.JSONDecodeError, ValueError):
        return ChunkResult(
            file=file_path,
            error="Model response could not be parsed as JSON.",
        )

    findings = []
    for item in data.get("findings", []) or []:
        message = (item.get("message") or "").strip()
        if not message:
            continue
        findings.append(
            Finding(
                file=file_path,
                line=item.get("line"),
                severity=Severity.from_str(item.get("severity", "warning")),
                category=Category.from_str(item.get("category", "other")),
                message=message,
                suggestion=item.get("suggestion") or None,
            )
        )

    return ChunkResult(file=file_path, findings=findings)


def run_review(
    diff_text: str,
    config: Config,
    provider: BaseProvider,
    on_progress: Optional[ProgressCallback] = None,
) -> ReviewResult:
    """Reviews an entire diff and returns the aggregated result.

    `on_progress` is called with a short human readable string before each
    file is reviewed, so the CLI can show live feedback on larger PRs.
    """

    files = parse_unified_diff(diff_text)
    result = ReviewResult(provider=provider.name, model=provider.model)

    reviewable: list[DiffFile] = []
    for diff_file in files:
        if diff_file.is_binary or diff_file.is_deleted:
            result.files_skipped += 1
            continue
        if is_ignored(diff_file.path, config.ignore):
            result.files_skipped += 1
            continue
        if not diff_file.hunks:
            result.files_skipped += 1
            continue
        reviewable.append(diff_file)

    if len(reviewable) > config.max_files:
        result.files_skipped += len(reviewable) - config.max_files
        reviewable = reviewable[: config.max_files]

    for diff_file in reviewable:
        if on_progress:
            on_progress(diff_file.path)

        chunks = _chunk_hunks(diff_file.hunks, config.max_diff_lines_per_chunk)
        for hunk_group in chunks:
            chunk_text = "\n".join(hunk.to_text() for hunk in hunk_group)
            chunk_result = review_chunk(
                provider=provider,
                file_path=diff_file.path,
                chunk_text=chunk_text,
                custom_rules=config.custom_rules,
                language_hints=config.language_hints,
                use_cache=config.cache_enabled,
            )
            if chunk_result.error:
                result.chunks_failed += 1
            result.findings.extend(chunk_result.findings)

        result.files_reviewed += 1

    threshold = Severity.from_str(config.severity_threshold)
    result.findings = [f for f in result.findings if f.severity.rank >= threshold.rank]

    return result
