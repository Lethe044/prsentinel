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
"""


def write_default_config(path: str = ".prsentinel.yml") -> Path:
    target = Path(path)
    target.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    return target
