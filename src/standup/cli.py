"""CLI entry point for Git Standup Bot.

Provides the `standup` command with all options for customizing report generation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from standup.config import load_config, InvalidProviderError, validate_provider
from standup.git_parser import parse_commits, parse_multiple_repos
from standup.grouper import group_commits
from standup.ai_summarizer import generate_summary
from standup.formatter import render_terminal, export_markdown
from standup.agent import run_developer_agent
from standup.standup_agent import run_standup_agent
from standup.encoding_helper import setup_safe_streams
from standup.timezone_helper import resolve_timezone

# Initialize stream wrapping for CP1254 and other non-UTF-8 consoles
setup_safe_streams()

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
    "--agent/--no-agent",
    default=False,
    help="Enable Tech Lead AI Agent to analyze commits for security, risk, and code quality.",
)
@click.option(
    "--standup-agent/--no-standup-agent",
    default=None,
    help="Enable AI Standup Agent to generate structured Completed/In Progress/Risks/Next Steps sections.",
)
@click.option(
    "--provider", "-p",
    type=click.Choice(["auto", "openai", "ollama", "gemini"], case_sensitive=False),
    default=None,
    help="AI provider to use. (default: auto)",
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
    help="How to group commits: 'type' (conventional type), 'branch' (groups by active/tip branch ref decoration; historical branch membership is not preserved by Git), or 'repo'. (default: type)",
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
    agent: bool,
    standup_agent: bool | None,
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
    try:
        cfg = load_config(cfg_path)
    except InvalidProviderError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    # Resolve timezone
    try:
        effective_timezone = resolve_timezone(cfg.timezone)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    # CLI arguments override config values
    effective_since = since or cfg.since
    effective_author = author or cfg.author
    effective_group_by = group_by or cfg.output.group_by
    effective_show_hashes = hashes if hashes is not None else cfg.output.show_hashes
    effective_export = export_path or cfg.output.export_path or None

    # AI settings
    effective_ai = ai if ai is not None else cfg.ai.enabled

    # Resolve and validate provider
    try:
        effective_provider = validate_provider(provider or cfg.ai.provider)
    except InvalidProviderError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    effective_standup_agent = standup_agent if standup_agent is not None else cfg.standup_agent

    # Resolve repo paths
    if repos:
        repo_paths = list(dict.fromkeys(str(Path(r).resolve()) for r in repos))
    elif cfg.repo_paths:
        repo_paths = list(dict.fromkeys(cfg.repo_paths))
    else:
        repo_paths = [str(Path.cwd())]

    # Parse commits
    commits = []
    errors = {}
    try:
        if len(repo_paths) == 1:
            commits = parse_commits(
                repo_paths[0],
                since=effective_since,
                author=effective_author,
            )
        else:
            commits, errors = parse_multiple_repos(
                repo_paths,
                since=effective_since,
                author=effective_author,
            )
    except (RuntimeError, FileNotFoundError) as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    # Handle multi-repo errors
    if errors:
        stderr_console = Console(stderr=True)
        if len(errors) == len(repo_paths):
            stderr_console.print("[red bold]Error: All repositories failed to parse:[/red bold]")
            for p, reason in errors.items():
                stderr_console.print(f"  - {p}: {reason}")
            sys.exit(1)
        else:
            stderr_console.print("[yellow bold]Warning: The following repositories were skipped due to errors:[/yellow bold]")
            for p, reason in errors.items():
                stderr_console.print(f"  - {p}: {reason}")

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
            elif effective_provider == "ollama":
                console.print(
                    "[yellow]⚠ AI summary unavailable. "
                    "Make sure Ollama is running.[/yellow]"
                )
            else:  # "auto" provider failed to resolve any active backend
                console.print(
                    "[yellow]⚠ AI summary unavailable. "
                    "To enable AI summaries, you can:\n"
                    "  1. Start local Ollama (highly recommended, free)\n"
                    "  2. Set GEMINI_API_KEY environment variable\n"
                    "  3. Set OPENAI_API_KEY environment variable[/yellow]"
                )

    # Agent Assessment (optional Tech Lead Agent)
    agent_assessment = None
    if agent and commits:
        console.print("[dim]🕵️ Tech Lead Agent analyzing code changes...[/dim]")
        agent_assessment = run_developer_agent(
            commits,
            provider=effective_provider,
            api_key=cfg.ai.api_key,
            openai_model=cfg.ai.openai_model,
            ollama_model=cfg.ai.ollama_model,
            ollama_url=cfg.ai.ollama_url,
            gemini_model=cfg.ai.gemini_model,
            gemini_api_key=cfg.ai.gemini_api_key,
        )

    # Standup Agent Assessment (optional AI Standup Agent)
    standup_assessment = None
    if effective_standup_agent:
        if effective_ai:
            console.print("[dim]🤖 AI Standup Agent analyzing activity...[/dim]")
            standup_assessment = run_standup_agent(
                commits,
                provider=effective_provider,
                api_key=cfg.ai.api_key,
                openai_model=cfg.ai.openai_model,
                ollama_model=cfg.ai.ollama_model,
                ollama_url=cfg.ai.ollama_url,
                gemini_model=cfg.ai.gemini_model,
                gemini_api_key=cfg.ai.gemini_api_key,
            )
        else:
            # --no-ai blocks LLM requests and runs deterministic local fallback
            from standup.standup_agent import get_deterministic_fallback
            standup_assessment = get_deterministic_fallback(commits)

    # Render to terminal
    render_terminal(
        repo_groups,
        author=display_author,
        ai_summary=ai_summary,
        show_hashes=effective_show_hashes,
        agent_assessment=agent_assessment,
        timezone=effective_timezone,
        standup_assessment=standup_assessment,
    )

    # Export to file if requested
    if effective_export:
        out = export_markdown(
            repo_groups,
            output_path=effective_export,
            author=display_author,
            ai_summary=ai_summary,
            show_hashes=effective_show_hashes,
            agent_assessment=agent_assessment,
            timezone=effective_timezone,
            standup_assessment=standup_assessment,
        )
        console.print(f"[green]✅ Report exported to {out}[/green]")


if __name__ == "__main__":
    main()
