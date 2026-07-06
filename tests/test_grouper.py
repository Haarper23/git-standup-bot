"""Tests for grouper module."""

from datetime import datetime

from standup.git_parser import Commit
from standup.grouper import (
    group_by_type,
    group_by_branch,
    group_by_repo,
    group_commits,
)


def _commit(
    subject: str = "feat: test",
    branch: str = "main",
    repo: str = "my-repo",
) -> Commit:
    """Helper to create a Commit with sensible defaults."""
    return Commit(
        hash="abc1234",
        author="Test User",
        date=datetime(2026, 7, 6, 10, 0, 0),
        subject=subject,
        body="",
        branch=branch,
        repo_name=repo,
    )


class TestGroupByType:
    """Test commit grouping by conventional commit type."""

    def test_single_type(self):
        commits = [
            _commit("feat: add login"),
            _commit("feat: add signup"),
        ]
        groups = group_by_type(commits)
        assert len(groups) == 1
        assert groups[0].key == "feat"
        assert groups[0].count == 2

    def test_multiple_types(self):
        commits = [
            _commit("feat: add login"),
            _commit("fix: resolve crash"),
            _commit("docs: update readme"),
        ]
        groups = group_by_type(commits)
        keys = [g.key for g in groups]
        assert "feat" in keys
        assert "fix" in keys
        assert "docs" in keys

    def test_unknown_type_grouped_as_other(self):
        commits = [_commit("Update something")]
        groups = group_by_type(commits)
        assert len(groups) == 1
        assert groups[0].key == "other"

    def test_empty_list(self):
        groups = group_by_type([])
        assert groups == []

    def test_type_order_preserved(self):
        """feat should come before fix in output."""
        commits = [
            _commit("fix: bug fix"),
            _commit("feat: new feature"),
        ]
        groups = group_by_type(commits)
        keys = [g.key for g in groups]
        assert keys.index("feat") < keys.index("fix")


class TestGroupByBranch:
    """Test commit grouping by branch name."""

    def test_single_branch(self):
        commits = [
            _commit("feat: a", branch="main"),
            _commit("fix: b", branch="main"),
        ]
        groups = group_by_branch(commits)
        assert len(groups) == 1
        assert groups[0].key == "main"

    def test_multiple_branches(self):
        commits = [
            _commit("feat: a", branch="main"),
            _commit("feat: b", branch="develop"),
            _commit("fix: c", branch="feature/login"),
        ]
        groups = group_by_branch(commits)
        assert len(groups) == 3


class TestGroupByRepo:
    """Test commit grouping by repository."""

    def test_single_repo(self):
        commits = [
            _commit("feat: a", repo="api"),
            _commit("fix: b", repo="api"),
        ]
        repo_groups = group_by_repo(commits)
        assert len(repo_groups) == 1
        assert repo_groups[0].repo_name == "api"

    def test_multiple_repos(self):
        commits = [
            _commit("feat: a", repo="api"),
            _commit("fix: b", repo="frontend"),
        ]
        repo_groups = group_by_repo(commits)
        assert len(repo_groups) == 2
        names = [rg.repo_name for rg in repo_groups]
        assert "api" in names
        assert "frontend" in names

    def test_commits_typed_within_repo(self):
        """Each repo should have its commits grouped by type."""
        commits = [
            _commit("feat: a", repo="api"),
            _commit("fix: b", repo="api"),
        ]
        repo_groups = group_by_repo(commits)
        rg = repo_groups[0]
        type_keys = [g.key for g in rg.groups]
        assert "feat" in type_keys
        assert "fix" in type_keys


class TestGroupCommits:
    """Test the main group_commits dispatcher."""

    def test_empty_commits(self):
        result = group_commits([])
        assert result == []

    def test_default_groups_by_type(self):
        commits = [_commit("feat: a"), _commit("fix: b")]
        result = group_commits(commits, group_by="type")
        assert len(result) == 1  # single repo
        assert result[0].total_commits == 2

    def test_group_by_branch(self):
        commits = [
            _commit("feat: a", branch="main"),
            _commit("feat: b", branch="dev"),
        ]
        result = group_commits(commits, group_by="branch")
        assert len(result) == 1  # single repo
        assert len(result[0].groups) == 2  # two branches
