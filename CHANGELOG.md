# Changelog

All notable changes to this project are documented in this file.

## [1.0.0] - Initial release

### Added

- Core review pipeline: unified diff parsing, per-file and per-hunk
  chunking, and structured JSON findings parsed from a model response.
- Five model providers: Groq, Gemini, and Ollama as free options, plus
  OpenAI and Anthropic for anyone bringing their own paid key.
- `prsentinel review` command with support for local git diffs, a saved
  diff file, or the current GitHub Actions pull request.
- Terminal output with a colored findings table, plus JSON and SARIF
  export formats.
- GitHub integration: a single, self-updating summary comment, inline
  comments on the exact changed lines, and automatic "Request changes"
  when a critical issue is found.
- `.prsentinel.yml` configuration file with per-project ignore patterns,
  custom review rules in plain English, and a configurable severity
  threshold and CI fail condition.
- Local response cache so repeated runs on the same diff do not spend
  API quota twice.
- A ready to use composite GitHub Action (`action.yml`) requiring no
  Docker image.
- `prsentinel init`, `prsentinel providers`, and `prsentinel clear-cache`
  utility commands.
- Full test suite covering the diff parser, config loading, ignore
  patterns, the reviewer pipeline, and all output formatters.
