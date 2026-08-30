"""Decides which changed files should be skipped during a review.

Patterns are simple gitignore-style globs (using fnmatch), not a full
gitignore implementation. That keeps the dependency list small while
covering the overwhelming majority of real world cases: lockfiles, build
output, vendored code, and generated assets.
"""

from __future__ import annotations

import fnmatch

DEFAULT_IGNORE_PATTERNS = [
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
    "go.sum",
    "*.min.js",
    "*.min.css",
    "*.map",
    "dist/**",
    "build/**",
    "node_modules/**",
    "vendor/**",
    ".venv/**",
    "venv/**",
    "*.svg",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.ico",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.pdf",
]


def is_ignored(path: str, patterns: list[str]) -> bool:
    """Returns True if `path` matches any of the given glob patterns."""

    normalized = path.replace("\\", "/")
    for pattern in patterns:
        pattern = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, pattern):
            return True
        # Allow a pattern like "dist/**" to also match "dist" alone and
        # match patterns without a leading path against any path segment.
        if "/" not in pattern and fnmatch.fnmatch(normalized.split("/")[-1], pattern):
            return True
    return False
