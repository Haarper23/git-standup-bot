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
from standup.agent import AgentAssessment
from standup.standup_agent import StandupAssessment


def _now_header(tz: datetime.tzinfo | None = None, now: datetime | None = None) -> str:
    """Get formatted current date string for report header."""
    if now is None:
        now = datetime.now(tz)
    else:
        if tz:
            if now.tzinfo is None:
                from datetime import timezone as dt_tz
                now = now.replace(tzinfo=dt_tz.utc).astimezone(tz)
            else:
                now = now.astimezone(tz)

    return now.strftime("%Y-%m-%d (%A)")


def render_terminal(
    repo_groups: list[RepoGroup],
    author: str = "",
    ai_summary: str | None = None,
    show_hashes: bool = False,
    agent_assessment: AgentAssessment | None = None,
    timezone: datetime.tzinfo | None = None,
    standup_assessment: StandupAssessment | None = None,
) -> None:
    """Render the standup report to the terminal using rich.

    Args:
        repo_groups: Grouped commit data.
        author: Author name for the header.
        ai_summary: Optional AI-generated summary.
        show_hashes: Whether to show commit hashes.
        agent_assessment: Optional Tech Lead Agent assessment.
        timezone: Optional configured timezone.
    """
    console = Console()

    total_commits = sum(rg.total_commits for rg in repo_groups)
    total_repos = len(repo_groups)

    # Header panel
    header_lines = [
        f"🚀 Standup Report — {_now_header(timezone)}",
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
        if not standup_assessment:
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

    # Agent Insights
    if agent_assessment:
        console.print()
        
        # Determine panel border color based on risk level
        risk = agent_assessment.risk_level.lower()
        if "high" in risk:
            border_style = "bright_red"
            risk_style = "bold bright_red"
        elif "medium" in risk:
            border_style = "yellow"
            risk_style = "bold yellow"
        else:
            border_style = "bright_blue"
            risk_style = "bold bright_blue"

        agent_text = Text()
        agent_text.append("🕵️ Tech Lead Agent Insights:\n", style="bold magenta")
        agent_text.append(f"\n• Risk Level: ", style="bold")
        agent_text.append(f"{agent_assessment.risk_level}\n", style=risk_style)
        
        agent_text.append("• Architectural Impact: ", style="bold")
        agent_text.append(f"{agent_assessment.impact_summary}\n", style="")
        
        if agent_assessment.security_code_quality:
            agent_text.append("\n⚠️ Security & Code Quality:\n", style="bold yellow")
            for item in agent_assessment.security_code_quality:
                agent_text.append(f"  - {item}\n", style="dim")
                
        if agent_assessment.recommended_next_steps:
            agent_text.append("\n📋 Recommended Next Steps:\n", style="bold green")
            for item in agent_assessment.recommended_next_steps:
                agent_text.append(f"  - {item}\n", style="")

        console.print(
            Panel(
                agent_text,
                border_style=border_style,
                padding=(1, 2),
            )
        )

    # AI Standup Agent
    if standup_assessment:
        console.print()
        agent_text = Text()
        agent_text.append("🤖 AI Standup Agent:\n", style="bold bright_green")

        if standup_assessment.warning:
            agent_text.append(f"\n⚠️ Warning: {standup_assessment.warning}\n", style="yellow")

        agent_text.append("\nCompleted:\n", style="bold green")
        for item in standup_assessment.completed:
            agent_text.append(f"  - {item}\n", style="")

        agent_text.append("\nIn Progress:\n", style="bold blue")
        for item in standup_assessment.in_progress:
            agent_text.append(f"  - {item}\n", style="")

        agent_text.append("\nRisks / Blockers:\n", style="bold red")
        for item in standup_assessment.risks_blockers:
            agent_text.append(f"  - {item}\n", style="")

        agent_text.append("\nNext Steps:\n", style="bold magenta")
        for item in standup_assessment.next_steps:
            agent_text.append(f"  - {item}\n", style="")

        console.print(
            Panel(
                agent_text,
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
    agent_assessment: AgentAssessment | None = None,
    timezone: datetime.tzinfo | None = None,
    standup_assessment: StandupAssessment | None = None,
) -> str:
    """Render the standup report as a Markdown string.

    Args:
        repo_groups: Grouped commit data.
        author: Author name for the header.
        ai_summary: Optional AI-generated summary.
        show_hashes: Whether to show commit hashes.
        agent_assessment: Optional Tech Lead Agent assessment.
        timezone: Optional configured tzinfo object.

    Returns:
        Complete Markdown report string.
    """
    lines: list[str] = []
    total_commits = sum(rg.total_commits for rg in repo_groups)

    # Header
    lines.append(f"# 🚀 Standup Report — {_now_header(timezone)}")
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
        if not standup_assessment:
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

    # Agent Insights
    if agent_assessment:
        lines.append("---")
        lines.append("")
        lines.append("## 🕵️ Tech Lead Agent Insights")
        lines.append("")
        lines.append(f"**Risk Level:** {agent_assessment.risk_level}")
        lines.append("")
        lines.append(f"**Architectural Impact:** {agent_assessment.impact_summary}")
        lines.append("")
        
        if agent_assessment.security_code_quality:
            lines.append("### ⚠️ Security & Code Quality")
            lines.append("")
            for item in agent_assessment.security_code_quality:
                lines.append(f"- {item}")
            lines.append("")
            
        if agent_assessment.recommended_next_steps:
            lines.append("### 📋 Recommended Next Steps")
            lines.append("")
            for item in agent_assessment.recommended_next_steps:
                lines.append(f"- {item}")
            lines.append("")
    # AI Standup Agent
    if standup_assessment:
        lines.append("---")
        lines.append("")
        lines.append("## 🤖 AI Standup Agent")
        lines.append("")
        if standup_assessment.warning:
            lines.append("> [!WARNING]")
            lines.append(f"> {standup_assessment.warning}")
            lines.append("")

        lines.append("### Completed")
        lines.append("")
        for item in standup_assessment.completed:
            lines.append(f"- {item}")
        lines.append("")

        lines.append("### In Progress")
        lines.append("")
        for item in standup_assessment.in_progress:
            lines.append(f"- {item}")
        lines.append("")

        lines.append("### Risks / Blockers")
        lines.append("")
        for item in standup_assessment.risks_blockers:
            lines.append(f"- {item}")
        lines.append("")

        lines.append("### Next Steps")
        lines.append("")
        for item in standup_assessment.next_steps:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def export_markdown(
    repo_groups: list[RepoGroup],
    output_path: str | Path,
    author: str = "",
    ai_summary: str | None = None,
    show_hashes: bool = False,
    agent_assessment: AgentAssessment | None = None,
    timezone: datetime.tzinfo | None = None,
    standup_assessment: StandupAssessment | None = None,
) -> Path:
    """Export the standup report to a Markdown file.

    Args:
        repo_groups: Grouped commit data.
        output_path: File path to write the report.
        author: Author name for the header.
        ai_summary: Optional AI-generated summary.
        show_hashes: Whether to show commit hashes.
        agent_assessment: Optional Tech Lead Agent assessment.
        timezone: Optional configured tzinfo object.
        standup_assessment: Optional Standup Agent assessment.

    Returns:
        Path to the written file.
    """
    content = render_markdown(
        repo_groups,
        author=author,
        ai_summary=ai_summary,
        show_hashes=show_hashes,
        agent_assessment=agent_assessment,
        timezone=timezone,
        standup_assessment=standup_assessment,
    )

    path = Path(output_path)
    path.write_text(content, encoding="utf-8")
    return path
