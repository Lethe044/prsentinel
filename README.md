# PR Sentinel

[![CI](https://github.com/Lethe044/prsentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/Lethe044/prsentinel/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/prsentinel-cli.svg)](https://pypi.org/project/prsentinel-cli/)
[![Python versions](https://img.shields.io/pypi/pyversions/prsentinel-cli.svg)](https://pypi.org/project/prsentinel-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Free, self-hosted AI code review for pull requests and merge requests.
Point it at a free provider like Groq, Gemini, or a local Ollama model and
it reads your diff, flags real problems, and leaves comments directly on
GitHub or GitLab. No subscription, no seat-based pricing, no vendor
lock-in.

If your team has a budget for a paid model, PR Sentinel works with your own
OpenAI or Anthropic key too. Nothing here requires it.

## Why this exists

Automated PR review tools are useful, but the well known ones are paid
products with per-seat pricing. That is a real cost for a solo developer, a
student project, or a small open source repository, even when the actual
review only needs a handful of API calls per pull request. PR Sentinel is
the same idea built as a small, auditable, self-hosted tool: you choose the
model, you hold the API key (or use none at all with a local model), and
the entire pipeline runs inside your own GitHub Actions job.

## What it does

- Reads the diff for a pull request (or a local `git diff`) and reviews
  only the changed lines, using surrounding context to understand intent.
- Works on both GitHub pull requests and GitLab merge requests.
- Flags bugs, security issues, performance problems, missing error
  handling, and missing tests, not personal style nitpicks.
- Posts a single summary comment on the pull request, plus inline comments
  on the specific lines with a problem, and updates that same comment on
  every push instead of piling up duplicates.
- Requests changes automatically when a critical issue is found, so it can
  act as a real merge gate if you want one.
- Also works as a [pre-commit](https://pre-commit.com) hook, reviewing
  staged changes before they are even pushed.
- Suggests a pull request title and description from a diff with
  `prsentinel summarize`, if you would rather not write one by hand.
- Reviews diff chunks concurrently, so larger pull requests finish faster.
- Works from the command line too, so you can review a diff before you even
  open the pull request.
- Exports findings as SARIF for the GitHub Security tab, or as plain JSON
  for your own tooling.
- Caches results per diff chunk so re-running a workflow does not spend
  API quota reviewing the same lines twice.

## Quickstart: GitHub Actions

Add this workflow at `.github/workflows/pr-sentinel.yml`:

```yaml
name: PR Sentinel

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Lethe044/prsentinel@v1
        with:
          provider: groq
          api-key: ${{ secrets.GROQ_API_KEY }}
```

Get a free Groq API key at [console.groq.com/keys](https://console.groq.com/keys),
add it as a repository secret named `GROQ_API_KEY`, and every new pull
request gets reviewed automatically.

## Quickstart: GitLab CI

Add this to `.gitlab-ci.yml`:

```yaml
prsentinel:
  image: python:3.12
  stage: test
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
  script:
    - pip install prsentinel-cli
    - prsentinel review --post-to-gitlab --provider groq
  variables:
    GROQ_API_KEY: $GROQ_API_KEY
```

Add `GROQ_API_KEY` and a `GITLAB_TOKEN` (a project access token with the
`api` scope) as masked CI/CD variables in your project settings, and every
merge request gets a summary note plus inline comments on the changed
lines.

## Quickstart: pre-commit hook

PR Sentinel also works as a [pre-commit](https://pre-commit.com) hook, so
you catch problems before they are even pushed. Add this to your
`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Lethe044/prsentinel
    rev: v1.1.0
    hooks:
      - id: prsentinel
```

This reviews your staged changes every time you run `git commit`, using
whichever provider and API key you have configured locally.

## Quickstart: command line

```bash
pip install prsentinel-cli

export GROQ_API_KEY=your-key-here
prsentinel review --base origin/main --head HEAD
```

This prints a table of findings straight to your terminal, before you even
push. Combine it with a pre-push git hook if you want a check before code
leaves your machine at all.

## Choosing a provider

| Provider  | Cost                          | Setup                                                             |
|-----------|--------------------------------|--------------------------------------------------------------------|
| groq      | Free tier                     | API key from console.groq.com/keys, set `GROQ_API_KEY`             |
| gemini    | Free tier                     | API key from aistudio.google.com/apikey, set `GEMINI_API_KEY`      |
| ollama    | Free, fully local             | Run `ollama serve` and pull a model, no key needed                 |
| openai    | Paid, bring your own key      | Set `OPENAI_API_KEY`                                                |
| anthropic | Paid, bring your own key      | Set `ANTHROPIC_API_KEY`                                             |

Run `prsentinel providers` at any time to see this list along with the
default model used for each one.

## Configuration

Run `prsentinel init` to write a starter `.prsentinel.yml` in your
repository root. Every field is optional and falls back to a sensible
default if the file does not exist at all.

```yaml
provider: groq
model:
severity_threshold: suggestion
fail_on: critical
max_files: 60
max_diff_lines_per_chunk: 350
ignore:
  - "*.lock"
  - "dist/**"
  - "node_modules/**"
  - "vendor/**"
custom_rules:
  - "Flag any hardcoded API keys or secrets"
  - "Require a docstring on every public function"
post_summary_comment: true
inline_comments: true
request_changes_on_critical: true
cache_enabled: true
max_workers: 4
show_footer: true
```

`custom_rules` is where PR Sentinel becomes specific to your project. Add
plain English instructions and they get appended to every review prompt,
alongside the general review.

`fail_on` controls the exit code (and therefore whether your CI check goes
red). Set it to `warning` for a stricter gate, or `suggestion` for the
strictest possible one.

`max_workers` controls how many diff chunks are reviewed at the same time.
Raising it speeds up large pull requests, at the cost of hitting a free
tier rate limit sooner.

Run `prsentinel validate-config` at any time to check a `.prsentinel.yml`
file for typos or invalid values without running a full review, useful as
a quick sanity check in CI before the real review step runs.

## Command line reference

```
prsentinel review           Review a diff and report findings
prsentinel summarize        Suggest a PR title and description from a diff
prsentinel init              Write a starter .prsentinel.yml
prsentinel validate-config   Check a .prsentinel.yml file for problems
prsentinel providers         List providers and setup instructions
prsentinel clear-cache       Delete the local review cache
```

Useful flags on `review`:

```
--base, --head        Git refs to diff (defaults to origin/main...HEAD)
--staged              Review staged changes instead of a branch diff
--diff-file           Review a saved unified diff file instead of running git
--provider, --model   Override the provider or model from config
--output              terminal (default), json, or sarif
--output-file         Write json/sarif output to a file
--post-to-github      Post results as a review on the current GitHub Actions PR
--post-to-gitlab      Post results as notes on the current GitLab CI merge request
--dry-run             Compute the review but do not post anything, just print it
--fail-on             Override the fail_on threshold for this run
--no-cache            Skip the local response cache for this run
```

## Suggesting a PR title and description

```bash
prsentinel summarize --base origin/main --head HEAD
```

Reads the same kind of diff as `review`, but instead of finding problems it
proposes a conventional-commit style title, a short summary, and a few
highlights. Handy when you are about to open a pull request and would
rather not write the description from scratch.

## How review comments look

PR Sentinel posts one summary comment with a small table of counts by
severity, followed by a breakdown per file, and inline comments on the
exact lines a finding refers to. If a critical issue is found and
`request_changes_on_critical` is enabled, the review is submitted as
"Request changes" instead of a plain comment, so it behaves like a real
review a teammate would leave.

## Limitations, on purpose

PR Sentinel reviews diffs, not your entire codebase, and it does not
replace a human reviewer. Language models make mistakes, including missing
real issues and occasionally flagging something that is not actually a
problem. Treat its output the way you would treat a review from a
thorough but fallible colleague: worth reading, not worth merging blindly
on faith either way. `custom_rules` and the `severity_threshold` and
`fail_on` settings let you tune how much weight to give it in your
workflow.

## Contributing

Bug reports, feature requests, and pull requests are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md) for how to get set up locally, how the
provider interface works, and what a good pull request looks like here.

## License

MIT. See [LICENSE](LICENSE).
