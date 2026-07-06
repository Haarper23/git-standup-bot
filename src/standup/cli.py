"""CLI entry point for Git Standup Bot.

Provides the `standup` command with all options for customizing report generation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from standup.config import load_config
from standup.git_parser import parse_commits, parse_multiple_repos
from standup.grouper import group_commits
from standup.ai_summarizer import generate_summary
from standup.formatter import render_terminal, export_markdown


console = Console()


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--since", "-s",
    default=None,
    help='Time range for commits. e.g., "yesterday", "3 days ago", "2026-07-01". (default: yesterday)',
)
@click.option(
    "--author", "-a",
    default=None,
    help="Filter by author name. (default: git config user.name)",
)
@click.option(
    "--repos", "-r",
    multiple=True,
    type=click.Path(exists=True, file_okay=False),
    help="Repository paths to scan. Can specify multiple times. (default: current directory)",
)
@click.option(
    "--ai/--no-ai",
    default=None,
    help="Enable/disable AI summary generation.",
)
@click.option(
    "--provider", "-p",
    type=click.Choice(["openai", "ollama", "gemini"], case_sensitive=False),
    default=None,
    help="AI provider to use. (default: openai)",
)
@click.option(
    "--export", "-e",
    "export_path",
    default=None,
    type=click.Path(),
    help="Export report to a Markdown file.",
)
@click.option(
    "--group-by", "-g",
    type=click.Choice(["type", "branch", "repo"], case_sensitive=False),
    default=None,
    help="How to group commits. (default: type)",
)
@click.option(
    "--hashes/--no-hashes",
    default=None,
    help="Show/hide commit hashes in output.",
)
@click.option(
    "--config", "-c",
    "config_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to .standup.toml config file.",
)
@click.version_option(package_name="git-standup-bot")
def main(
    since: str | None,
    author: str | None,
    repos: tuple[str, ...],
    ai: bool | None,
    provider: str | None,
    export_path: str | None,
    group_by: str | None,
    hashes: bool | None,
    config_path: str | None,
) -> None:
    """🚀 Git Standup Bot — Generate daily standup reports from your git activity.

    Scans your git repositories, groups commits by type, and optionally
    generates an AI-powered summary for your daily standup meeting.

    \b
    Examples:
      standup                          # Current repo, last 24h
      standup --since "3 days ago"     # Custom time range
      standup -r ~/project1 -r ~/project2  # Multiple repos
      standup --ai                     # With AI summary
      standup --export report.md       # Save as Markdown
    """
    # Load config file
    cfg_path = Path(config_path) if config_path else None
    cfg = load_config(cfg_path)

    # CLI arguments override config values
    effective_since = since or cfg.since
    effective_author = author or cfg.author
    effective_group_by = group_by or cfg.output.group_by
    effective_show_hashes = hashes if hashes is not None else cfg.output.show_hashes
    effective_export = export_path or cfg.output.export_path or None

    # AI settings
    effective_ai = ai if ai is not None else cfg.ai.enabled
    effective_provider = provider or cfg.ai.provider

    # Resolve repo paths
    if repos:
        repo_paths = [str(Path(r).resolve()) for r in repos]
    elif cfg.repo_paths:
        repo_paths = cfg.repo_paths
    else:
        repo_paths = [str(Path.cwd())]

    # Parse commits
    try:
        if len(repo_paths) == 1:
            commits = parse_commits(
                repo_paths[0],
                since=effective_since,
                author=effective_author,
            )
        else:
            commits = parse_multiple_repos(
                repo_paths,
                since=effective_since,
                author=effective_author,
            )
    except RuntimeError as e:
        console.print(f"[red bold]Error:[/red bold] {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"[red bold]Error:[/red bold] {e}")
        sys.exit(1)

    # Resolve author for display
    display_author = effective_author
    if not display_author and commits:
        display_author = commits[0].author

    # Group commits
    repo_groups = group_commits(commits, group_by=effective_group_by)

    # AI summary (optional)
    ai_summary: str | None = None
    if effective_ai and commits:
        console.print("[dim]🤖 Generating AI summary...[/dim]")
        ai_summary = generate_summary(
            commits,
            provider=effective_provider,
            api_key=cfg.ai.api_key,
            openai_model=cfg.ai.openai_model,
            ollama_model=cfg.ai.ollama_model,
            ollama_url=cfg.ai.ollama_url,
            gemini_model=cfg.ai.gemini_model,
            gemini_api_key=cfg.ai.gemini_api_key,
        )
        if ai_summary is None:
            if effective_provider == "openai":
                console.print(
                    "[yellow]⚠ AI summary unavailable. "
                    "Set OPENAI_API_KEY environment variable.[/yellow]"
                )
            elif effective_provider == "gemini":
                console.print(
                    "[yellow]⚠ AI summary unavailable. "
                    "Set GEMINI_API_KEY environment variable.[/yellow]"
                )
            else:
                console.print(
                    "[yellow]⚠ AI summary unavailable. "
                    "Make sure Ollama is running.[/yellow]"
                )

    # Render to terminal
    render_terminal(
        repo_groups,
        author=display_author,
        ai_summary=ai_summary,
        show_hashes=effective_show_hashes,
    )

    # Export to file if requested
    if effective_export:
        out = export_markdown(
            repo_groups,
            output_path=effective_export,
            author=display_author,
            ai_summary=ai_summary,
            show_hashes=effective_show_hashes,
        )
        console.print(f"[green]✅ Report exported to {out}[/green]")


if __name__ == "__main__":
    main()
