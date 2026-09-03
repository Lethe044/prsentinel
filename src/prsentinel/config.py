"""Loads and validates PR Sentinel configuration.

Configuration lives in an optional `.prsentinel.yml` file at the repository
root. Every field has a sensible default, so PR Sentinel works with zero
configuration beyond an API key (or none at all, if using Ollama).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from prsentinel.ignore import DEFAULT_IGNORE_PATTERNS

DEFAULT_CONFIG_FILENAMES = (".prsentinel.yml", ".prsentinel.yaml")

VALID_PROVIDERS = ("groq", "gemini", "ollama", "openai", "anthropic")
VALID_SEVERITIES = ("suggestion", "warning", "critical")


@dataclass
class Config:
    provider: str = "groq"
    model: Optional[str] = None
    severity_threshold: str = "suggestion"
    fail_on: str = "critical"
    max_files: int = 60
    max_diff_lines_per_chunk: int = 350
    ignore: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_PATTERNS))
    custom_rules: list[str] = field(default_factory=list)
    language_hints: bool = True
    post_summary_comment: bool = True
    inline_comments: bool = True
    request_changes_on_critical: bool = True
    cache_enabled: bool = True
    api_base: Optional[str] = None
    max_workers: int = 4
    show_footer: bool = True
    min_confidence: str = "low"
    category_severity_floor: dict = field(default_factory=lambda: {"security": "warning"})
    enable_suppression_comments: bool = True

    @staticmethod
    def load(path: Optional[str] = None) -> "Config":
        """Loads config from an explicit path, the default filenames in the
        current directory, or falls back to defaults if none exist.
        """

        config = Config()
        candidate = Path(path) if path else _find_default_config()
        if candidate is None or not candidate.exists():
            return config

        with open(candidate, "r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}

        for key, value in raw.items():
            attr = key.replace("-", "_")
            if hasattr(config, attr):
                setattr(config, attr, value)

        return config

    def api_key_env_var(self) -> str:
        return {
            "groq": "GROQ_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "ollama": "",
        }.get(self.provider, "")

    def resolved_api_key(self) -> Optional[str]:
        env_var = self.api_key_env_var()
        if not env_var:
            return None
        return os.environ.get(env_var)


def _find_default_config() -> Optional[Path]:
    for filename in DEFAULT_CONFIG_FILENAMES:
        candidate = Path.cwd() / filename
        if candidate.exists():
            return candidate
    return None


DEFAULT_CONFIG_TEMPLATE = """\
# PR Sentinel configuration
# Full reference: https://github.com/Lethe044/prsentinel#configuration

# Which provider to use: groq, gemini, ollama, openai, or anthropic
provider: groq

# Leave blank to use the provider's recommended default model
model:

# Minimum severity to report: suggestion, warning, or critical
severity_threshold: suggestion

# Minimum severity that should make the CI check fail
fail_on: critical

# Safety limits so a huge PR does not burn through your API quota
max_files: 60
max_diff_lines_per_chunk: 350

# Glob patterns for files that should never be reviewed
ignore:
  - "*.lock"
  - "dist/**"
  - "node_modules/**"
  - "vendor/**"

# Extra instructions specific to your project or team, in plain English
custom_rules: []

# Behaviour when running inside a GitHub Action
post_summary_comment: true
inline_comments: true
request_changes_on_critical: true

# Cache results per commit so re-running a workflow does not re-spend quota
cache_enabled: true

# How many diff chunks to review at the same time. Higher is faster but
# spends a free tier rate limit faster too.
max_workers: 4

# Adds a small "powered by PR Sentinel" line at the bottom of the summary
# comment. Turn off if you would rather keep comments unbranded.
show_footer: true

# Drop findings below this confidence level: low, medium, or high.
# "low" keeps everything the model reports.
min_confidence: low

# Force a minimum severity for specific categories, regardless of what the
# model assigned. Useful to make sure security findings are never quietly
# reported as a mere suggestion.
category_severity_floor:
  security: warning

# Lets you silence a specific finding with a comment in your code, the
# same way you would silence a linter: prsentinel-ignore-line,
# prsentinel-ignore-next-line, or prsentinel-ignore-file.
enable_suppression_comments: true
"""


def write_default_config(path: str = ".prsentinel.yml") -> Path:
    target = Path(path)
    target.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    return target


def validate_config(config: Config) -> list[str]:
    """Checks a loaded Config for values that would cause a confusing
    failure later, and returns a list of human readable problems. An empty
    list means the config is valid.
    """

    errors = []

    if config.provider not in VALID_PROVIDERS:
        errors.append(
            f"provider '{config.provider}' is not one of: "
            f"{', '.join(VALID_PROVIDERS)}"
        )

    if config.severity_threshold not in VALID_SEVERITIES:
        errors.append(
            f"severity_threshold '{config.severity_threshold}' is not one "
            f"of: {', '.join(VALID_SEVERITIES)}"
        )

    if config.fail_on not in VALID_SEVERITIES:
        errors.append(
            f"fail_on '{config.fail_on}' is not one of: "
            f"{', '.join(VALID_SEVERITIES)}"
        )

    if not isinstance(config.max_files, int) or config.max_files <= 0:
        errors.append("max_files must be a positive integer")

    if not isinstance(config.max_diff_lines_per_chunk, int) or config.max_diff_lines_per_chunk <= 0:
        errors.append("max_diff_lines_per_chunk must be a positive integer")

    if not isinstance(config.max_workers, int) or config.max_workers <= 0:
        errors.append("max_workers must be a positive integer")

    if not isinstance(config.ignore, list) or not all(isinstance(p, str) for p in config.ignore):
        errors.append("ignore must be a list of strings")

    if not isinstance(config.custom_rules, list) or not all(
        isinstance(r, str) for r in config.custom_rules
    ):
        errors.append("custom_rules must be a list of strings")

    if config.min_confidence not in ("low", "medium", "high"):
        errors.append("min_confidence must be one of: low, medium, high")

    if not isinstance(config.category_severity_floor, dict):
        errors.append("category_severity_floor must be a mapping of category to severity")
    else:
        for category, severity in config.category_severity_floor.items():
            if severity not in VALID_SEVERITIES:
                errors.append(
                    f"category_severity_floor['{category}'] = '{severity}' "
                    f"is not one of: {', '.join(VALID_SEVERITIES)}"
                )

    return errors
