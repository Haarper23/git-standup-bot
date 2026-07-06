"""Output formatter — renders standup reports to terminal and Markdown.

Uses `rich` for colorful terminal output and builds Markdown strings for export.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from standup.grouper import RepoGroup


def _now_header() -> str:
    """Get formatted current date string for report header."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d (%A)")


def render_terminal(
    repo_groups: list[RepoGroup],
    author: str = "",
    ai_summary: str | None = None,
    show_hashes: bool = False,
) -> None:
    """Render the standup report to the terminal using rich.

    Args:
        repo_groups: Grouped commit data.
        author: Author name for the header.
        ai_summary: Optional AI-generated summary.
        show_hashes: Whether to show commit hashes.
    """
    console = Console()

    total_commits = sum(rg.total_commits for rg in repo_groups)
    total_repos = len(repo_groups)

    # Header panel
    header_lines = [
        f"🚀 Standup Report — {_now_header()}",
        f"Author: {author or 'All'} │ Repos: {total_repos} │ Commits: {total_commits}",
    ]
    console.print()
    console.print(
        Panel(
            "\n".join(header_lines),
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )

    if total_commits == 0:
        console.print()
        console.print(
            "  [dim italic]No commits found for the specified period.[/dim italic]"
        )
        console.print()
        return

    # Render each repo
    for rg in repo_groups:
        console.print()
        console.print(
            f"  [bold bright_blue]📦 {rg.repo_name}[/bold bright_blue]"
            f"  [dim]({rg.total_commits} commits)[/dim]"
        )

        table = Table(
            show_header=True,
            header_style="bold",
            border_style="dim",
            padding=(0, 1),
            expand=False,
        )
        table.add_column("Category", style="bold", min_width=14)
        if show_hashes:
            table.add_column("Hash", style="dim cyan", width=9)
        table.add_column("Changes", min_width=40)

        for group in rg.groups:
            first = True
            for commit in group.commits:
                category = f"{group.emoji} {group.label}" if first else ""
                row: list[str] = [category]

                if show_hashes:
                    row.append(commit.short_hash)

                row.append(commit.clean_subject)
                table.add_row(*row)
                first = False

        console.print(table)

    # AI Summary
    if ai_summary:
        console.print()
        summary_text = Text()
        summary_text.append("🤖 AI Summary:\n", style="bold bright_green")
        for line in ai_summary.strip().split("\n"):
            summary_text.append(f"  {line}\n", style="")

        console.print(
            Panel(
                summary_text,
                border_style="bright_green",
                padding=(1, 2),
            )
        )

    console.print()


def render_markdown(
    repo_groups: list[RepoGroup],
    author: str = "",
    ai_summary: str | None = None,
    show_hashes: bool = False,
) -> str:
    """Render the standup report as a Markdown string.

    Args:
        repo_groups: Grouped commit data.
        author: Author name for the header.
        ai_summary: Optional AI-generated summary.
        show_hashes: Whether to show commit hashes.

    Returns:
        Complete Markdown report string.
    """
    lines: list[str] = []
    total_commits = sum(rg.total_commits for rg in repo_groups)

    # Header
    lines.append(f"# 🚀 Standup Report — {_now_header()}")
    lines.append("")
    lines.append(
        f"**Author:** {author or 'All'} | "
        f"**Repos:** {len(repo_groups)} | "
        f"**Commits:** {total_commits}"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    if total_commits == 0:
        lines.append("_No commits found for the specified period._")
        return "\n".join(lines)

    # Repos
    for rg in repo_groups:
        lines.append(f"## 📦 {rg.repo_name} ({rg.total_commits} commits)")
        lines.append("")

        for group in rg.groups:
            lines.append(f"### {group.emoji} {group.label}")
            lines.append("")
            for commit in group.commits:
                hash_part = f"`{commit.short_hash}` " if show_hashes else ""
                lines.append(f"- {hash_part}{commit.clean_subject}")
            lines.append("")

    # AI Summary
    if ai_summary:
        lines.append("---")
        lines.append("")
        lines.append("## 🤖 AI Summary")
        lines.append("")
        lines.append(ai_summary.strip())
        lines.append("")

    return "\n".join(lines)


def export_markdown(
    repo_groups: list[RepoGroup],
    output_path: str | Path,
    author: str = "",
    ai_summary: str | None = None,
    show_hashes: bool = False,
) -> Path:
    """Export the standup report to a Markdown file.

    Args:
        repo_groups: Grouped commit data.
        output_path: File path to write the report.
        author: Author name for the header.
        ai_summary: Optional AI-generated summary.
        show_hashes: Whether to show commit hashes.

    Returns:
        Path to the written file.
    """
    content = render_markdown(
        repo_groups,
        author=author,
        ai_summary=ai_summary,
        show_hashes=show_hashes,
    )

    path = Path(output_path)
    path.write_text(content, encoding="utf-8")
    return path
