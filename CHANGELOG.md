# Changelog

All notable changes to this project are documented in this file.

## [1.2.0]

### Added

- Inline suppression comments: `prsentinel-ignore-line`,
  `prsentinel-ignore-next-line`, and `prsentinel-ignore-file` silence
  findings the same way a linter comment would. Works with any comment
  syntax, and can be turned off with `enable_suppression_comments: false`.
- Findings now carry a confidence level (low, medium, high). Filter noise
  out with `min_confidence` in `.prsentinel.yml`.
- `category_severity_floor` config: forces a minimum severity for a
  category regardless of what the model assigned. Defaults to
  `security: warning`, so a security finding is never silently downgraded
  to a mere suggestion.
- Docker image published to `ghcr.io/lethe044/prsentinel` on every
  release, for running PR Sentinel without installing Python.
- `--output html`: renders a single, dependency-free HTML report, useful
  as a CI artifact.
- `prsentinel stats`: shows how many responses are stored in the local
  cache and how much disk space they use.

### Changed

- `Finding` objects now include a `confidence` field in JSON and SARIF
  output.

## [1.1.0]

### Added

- GitLab CI support: `prsentinel review --post-to-gitlab` posts a summary
  note and inline discussions on a GitLab merge request, using the same
  review pipeline as GitHub.
- `prsentinel summarize`: suggests a pull request title, a short summary,
  and a few highlights from a diff.
- `--staged` flag and a `.pre-commit-hooks.yaml` definition, so PR Sentinel
  can run as a [pre-commit](https://pre-commit.com) hook against staged
  changes before a commit is even made.
- `prsentinel validate-config`: checks a `.prsentinel.yml` file for
  invalid values without running a full review.
- `--dry-run` flag on `review`: computes the review and prints what would
  be posted, without actually posting to GitHub or GitLab.
- Diff chunks are now reviewed concurrently (`max_workers` in config),
  which noticeably speeds up review of larger pull requests.
- Optional branding footer on the summary comment, linking back to the
  project. Controlled by `show_footer` in config.

### Changed

- `format_summary_comment` now accepts a `show_footer` argument.

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
