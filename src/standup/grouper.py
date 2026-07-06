"""Commit grouper — organizes commits by type, branch, or repository.

Groups parsed Commit objects into categorized sections for display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from standup.git_parser import Commit


# Emoji and label mapping for conventional commit types
COMMIT_TYPE_META: dict[str, tuple[str, str]] = {
    "feat":     ("✨", "Features"),
    "fix":      ("🐛", "Bug Fixes"),
    "docs":     ("📝", "Documentation"),
    "style":    ("🎨", "Style"),
    "refactor": ("♻️",  "Refactoring"),
    "perf":     ("⚡", "Performance"),
    "test":     ("🧪", "Tests"),
    "build":    ("📦", "Build"),
    "ci":       ("🔧", "CI/CD"),
    "chore":    ("🔨", "Chores"),
    "revert":   ("⏪", "Reverts"),
    "other":    ("📌", "Other"),
}


@dataclass
class CommitGroup:
    """A named group of related commits."""

    key: str
    label: str
    emoji: str
    commits: list[Commit] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.commits)


@dataclass
class RepoGroup:
    """Commits grouped under a single repository."""

    repo_name: str
    groups: list[CommitGroup] = field(default_factory=list)

    @property
    def total_commits(self) -> int:
        return sum(g.count for g in self.groups)


def _get_type_meta(commit_type: str) -> tuple[str, str]:
    """Get emoji and label for a commit type.

    Args:
        commit_type: Conventional commit type string.

    Returns:
        Tuple of (emoji, label).
    """
    return COMMIT_TYPE_META.get(commit_type, COMMIT_TYPE_META["other"])


def group_by_type(commits: list[Commit]) -> list[CommitGroup]:
    """Group commits by their conventional commit type.

    Args:
        commits: List of Commit objects to group.

    Returns:
        List of CommitGroup objects, ordered by predefined type order.
    """
    buckets: dict[str, list[Commit]] = defaultdict(list)

    for commit in commits:
        buckets[commit.commit_type].append(commit)

    # Order by predefined type order, then alphabetically for unknown types
    type_order = list(COMMIT_TYPE_META.keys())
    groups: list[CommitGroup] = []

    for ctype in type_order:
        if ctype in buckets:
            emoji, label = _get_type_meta(ctype)
            groups.append(
                CommitGroup(
                    key=ctype,
                    label=label,
                    emoji=emoji,
                    commits=buckets[ctype],
                )
            )

    return groups


def group_by_branch(commits: list[Commit]) -> list[CommitGroup]:
    """Group commits by their branch name.

    Args:
        commits: List of Commit objects to group.

    Returns:
        List of CommitGroup objects, one per branch.
    """
    buckets: dict[str, list[Commit]] = defaultdict(list)

    for commit in commits:
        buckets[commit.branch].append(commit)

    groups: list[CommitGroup] = []
    for branch_name in sorted(buckets.keys()):
        groups.append(
            CommitGroup(
                key=branch_name,
                label=branch_name,
                emoji="🌿",
                commits=buckets[branch_name],
            )
        )

    return groups


def group_by_repo(commits: list[Commit]) -> list[RepoGroup]:
    """Group commits first by repository, then by commit type within each repo.

    Args:
        commits: List of Commit objects from potentially multiple repos.

    Returns:
        List of RepoGroup objects, each containing typed CommitGroups.
    """
    repo_buckets: dict[str, list[Commit]] = defaultdict(list)

    for commit in commits:
        repo_buckets[commit.repo_name].append(commit)

    repo_groups: list[RepoGroup] = []
    for repo_name in sorted(repo_buckets.keys()):
        typed_groups = group_by_type(repo_buckets[repo_name])
        repo_groups.append(
            RepoGroup(
                repo_name=repo_name,
                groups=typed_groups,
            )
        )

    return repo_groups


def group_commits(
    commits: list[Commit],
    group_by: str = "type",
) -> list[RepoGroup]:
    """Group commits according to the specified strategy.

    Always returns RepoGroup structure for consistent formatting.

    Args:
        commits: List of Commit objects.
        group_by: Grouping strategy — "type", "branch", or "repo".

    Returns:
        List of RepoGroup objects.
    """
    if not commits:
        return []

    if group_by == "repo":
        return group_by_repo(commits)

    # For "type" and "branch", wrap in a single RepoGroup per repo
    repo_buckets: dict[str, list[Commit]] = defaultdict(list)
    for commit in commits:
        repo_buckets[commit.repo_name].append(commit)

    repo_groups: list[RepoGroup] = []
    for repo_name in sorted(repo_buckets.keys()):
        if group_by == "branch":
            groups = group_by_branch(repo_buckets[repo_name])
        else:  # "type" is default
            groups = group_by_type(repo_buckets[repo_name])

        repo_groups.append(
            RepoGroup(repo_name=repo_name, groups=groups)
        )

    return repo_groups
