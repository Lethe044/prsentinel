from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from prsentinel import __version__, cache
from prsentinel.config import Config, write_default_config
from prsentinel.formatters.json_formatter import format_json
from prsentinel.formatters.markdown import MARKER, format_inline_comments, format_summary_comment
from prsentinel.formatters.sarif import format_sarif
from prsentinel.formatters.terminal import print_review
from prsentinel.github_client import GitHubClient, GitHubClientError
from prsentinel.models import Severity
from prsentinel.providers import PROVIDERS, get_provider
from prsentinel.providers.base import ProviderError
from prsentinel.reviewer import run_review

console = Console()


def _get_git_diff(base: str, head: str) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--unified=3", f"{base}...{head}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        raise click.ClickException(
            "git was not found on PATH. PR Sentinel needs git to compute a diff."
        )
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(
            f"git diff failed: {exc.stderr.strip() or exc}"
        )
    return result.stdout


@click.group()
@click.version_option(version=__version__, prog_name="prsentinel")
def main() -> None:
    """PR Sentinel: free, self-hosted AI code review for pull requests."""


@main.command()
@click.option("--path", default=".prsentinel.yml", show_default=True, help="Where to write the config file.")
@click.option("--force", is_flag=True, help="Overwrite the file if it already exists.")
def init(path: str, force: bool) -> None:
    """Writes a starter .prsentinel.yml in the current directory."""

    target = Path(path)
    if target.exists() and not force:
        raise click.ClickException(
            f"{path} already exists. Pass --force to overwrite it."
        )
    write_default_config(path)
    console.print(f"[green]Wrote {path}[/green]")


@main.command()
def providers() -> None:
    """Lists available providers and how to set each one up."""

    console.print("\n[bold]Free providers[/bold]")
    console.print("  groq     - console.groq.com/keys, set GROQ_API_KEY")
    console.print("  gemini   - aistudio.google.com/apikey, set GEMINI_API_KEY")
    console.print("  ollama   - fully local, run 'ollama serve', no key needed")
    console.print("\n[bold]Paid providers (bring your own key)[/bold]")
    console.print("  openai      - set OPENAI_API_KEY")
    console.print("  anthropic   - set ANTHROPIC_API_KEY")
    console.print(f"\nDefault models: {', '.join(f'{n}={p.default_model}' for n, p in PROVIDERS.items())}\n")


@main.command(name="clear-cache")
def clear_cache() -> None:
    """Deletes the local review cache."""

    removed = cache.clear()
    console.print(f"[green]Removed {removed} cached response(s).[/green]")


@main.command()
@click.option("--base", default="origin/main", show_default=True, help="Base ref to diff against.")
@click.option("--head", default="HEAD", show_default=True, help="Head ref to diff.")
@click.option("--diff-file", type=click.Path(exists=True), help="Review a saved unified diff file instead of running git.")
@click.option("--config", "config_path", type=click.Path(exists=True), help="Path to a .prsentinel.yml file.")
@click.option("--provider", help="Override the provider from config (groq, gemini, ollama, openai, anthropic).")
@click.option("--model", help="Override the model from config.")
@click.option("--api-key", help="Override the API key from the environment.")
@click.option("--output", type=click.Choice(["terminal", "json", "sarif"]), default="terminal", show_default=True)
@click.option("--output-file", type=click.Path(), help="Write --output json/sarif to a file instead of stdout.")
@click.option("--post-to-github", is_flag=True, help="Post results as a review on the current GitHub Actions pull request.")
@click.option("--no-cache", is_flag=True, help="Disable the local response cache for this run.")
@click.option("--fail-on", type=click.Choice(["suggestion", "warning", "critical"]), help="Override the fail_on threshold from config.")
def review(
    base: str,
    head: str,
    diff_file: str | None,
    config_path: str | None,
    provider: str | None,
    model: str | None,
    api_key: str | None,
    output: str,
    output_file: str | None,
    post_to_github: bool,
    no_cache: bool,
    fail_on: str | None,
) -> None:
    """Reviews a diff and reports findings."""

    config = Config.load(config_path)
    if provider:
        config.provider = provider
    if model:
        config.model = model
    if no_cache:
        config.cache_enabled = False
    if fail_on:
        config.fail_on = fail_on

    github_client = None
    pr_context = None
    if post_to_github:
        try:
            github_client, pr_context = GitHubClient.from_event()
        except GitHubClientError as exc:
            raise click.ClickException(str(exc))
        diff_text = github_client.get_pull_diff(pr_context)
    elif diff_file:
        diff_text = Path(diff_file).read_text(encoding="utf-8")
    else:
        diff_text = _get_git_diff(base, head)

    if not diff_text.strip():
        console.print("[green]No changes to review.[/green]")
        sys.exit(0)

    resolved_key = api_key or config.resolved_api_key()
    try:
        provider_instance = get_provider(
            config.provider, resolved_key, config.model, config.api_base
        )
    except ProviderError as exc:
        raise click.ClickException(str(exc))

    if provider_instance.requires_api_key() and not resolved_key:
        env_var = config.api_key_env_var()
        raise click.ClickException(
            f"No API key found for provider '{config.provider}'. Set "
            f"{env_var}, pass --api-key, or run 'prsentinel providers' for "
            "setup instructions."
        )

    def on_progress(file_path: str) -> None:
        if output == "terminal":
            console.print(f"[dim]Reviewing {file_path}...[/dim]")

    try:
        result = run_review(diff_text, config, provider_instance, on_progress)
    except ProviderError as exc:
        raise click.ClickException(str(exc))

    if output == "terminal":
        print_review(result, console)
    elif output == "json":
        rendered = json.dumps(format_json(result), indent=2)
        _write_output(rendered, output_file)
    elif output == "sarif":
        rendered = json.dumps(format_sarif(result), indent=2)
        _write_output(rendered, output_file)

    if post_to_github and github_client and pr_context:
        _post_github_review(github_client, pr_context, result, config)

    fail_threshold = Severity.from_str(config.fail_on)
    if result.findings_at_or_above(fail_threshold):
        sys.exit(1)


def _write_output(rendered: str, output_file: str | None) -> None:
    if output_file:
        Path(output_file).write_text(rendered, encoding="utf-8")
        console.print(f"[green]Wrote {output_file}[/green]")
    else:
        click.echo(rendered)


def _post_github_review(github_client: GitHubClient, pr_context, result, config: Config) -> None:
    summary = format_summary_comment(result)

    if config.post_summary_comment:
        try:
            github_client.upsert_summary_comment(pr_context, summary, MARKER)
        except GitHubClientError as exc:
            console.print(f"[yellow]Could not post summary comment: {exc}[/yellow]")

    critical_present = any(f.severity == Severity.CRITICAL for f in result.findings)
    event = (
        "REQUEST_CHANGES"
        if critical_present and config.request_changes_on_critical
        else "COMMENT"
    )

    inline_comments = format_inline_comments(result) if config.inline_comments else []

    try:
        github_client.submit_review(pr_context, event, summary, inline_comments)
    except GitHubClientError as exc:
        console.print(f"[yellow]Could not submit review: {exc}[/yellow]")


if __name__ == "__main__":
    main()
