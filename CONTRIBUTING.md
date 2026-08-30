# Contributing to PR Sentinel

Thanks for taking the time to contribute. This project stays useful because
of issues, bug reports, and pull requests from people who actually run it on
real pull requests, so any contribution is welcome, big or small.

## Getting set up

```
git clone https://github.com/Lethe044/prsentinel.git
cd prsentinel
pip install -e ".[dev]"
```

This installs PR Sentinel in editable mode along with the test dependencies.

## Running the tests

```
pytest
```

The test suite does not call any real provider API. Provider calls are
mocked, so tests run instantly and do not need an API key.

## Adding a new provider

Providers live in `src/prsentinel/providers/`. Each one is a small class
that extends `BaseProvider` and implements a single method, `complete`.
Look at `groq_provider.py` for a short, complete example. Once your provider
class exists, register it in `src/prsentinel/providers/__init__.py` and it
becomes available everywhere: the CLI, the config file, and the GitHub
Action.

A good provider implementation:

- Raises `ProviderError` with a clear, actionable message on failure
  (missing key, network error, rate limit, unexpected response shape)
  instead of letting a raw exception escape.
- Does not silently swallow errors.
- Has a sensible `default_model`.

## Code style

There is no separate linter configuration yet. Keep new code close to the
style already in the file you are editing: type hints on public functions,
short docstrings on modules and non-obvious functions, and small, focused
functions over long ones.

## Submitting a pull request

1. Fork the repository and create a branch from `main`.
2. Make your change, with tests for any new behavior.
3. Run `pytest` and make sure everything passes.
4. Open a pull request describing what changed and why.

PR Sentinel reviews its own pull requests using the tool itself, so do not
be surprised if you see an automated review comment. It is one more set of
eyes, not a gate; a human still reviews every change.

## Reporting bugs and requesting features

Use the issue templates. The more specific the reproduction steps, the
faster a fix can happen.
