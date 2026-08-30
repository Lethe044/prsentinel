from __future__ import annotations

from prsentinel.models import ReviewResult


def format_json(result: ReviewResult) -> dict:
    return {
        "provider": result.provider,
        "model": result.model,
        "files_reviewed": result.files_reviewed,
        "files_skipped": result.files_skipped,
        "chunks_failed": result.chunks_failed,
        "counts": result.counts_by_severity(),
        "findings": [f.to_dict() for f in result.findings],
    }
