"""Tests for formatter module."""

from datetime import datetime

from standup.git_parser import Commit
from standup.grouper import CommitGroup, RepoGroup
from standup.formatter import render_markdown


def _commit(subject: str = "feat: test", repo: str = "my-repo") -> Commit:
    """Helper to create a Commit with sensible defaults."""
    return Commit(
        hash="abc1234567890",
        author="Test User",
        date=datetime(2026, 7, 6, 10, 0, 0),
        subject=subject,
        body="",
        branch="main",
        repo_name=repo,
    )


def _repo_group(
    name: str = "my-repo",
    groups: list[CommitGroup] | None = None,
) -> RepoGroup:
    """Helper to create a RepoGroup."""
    if groups is None:
        groups = [
            CommitGroup(
                key="feat",
                label="Features",
                emoji="✨",
                commits=[_commit("feat: add login")],
            )
        ]
    return RepoGroup(repo_name=name, groups=groups)


class TestRenderMarkdown:
    """Test Markdown report generation."""

    def test_contains_header(self):
        md = render_markdown([_repo_group()], author="Test User")
        assert "Standup Report" in md
        assert "Test User" in md

    def test_contains_repo_name(self):
        md = render_markdown([_repo_group(name="my-api")])
        assert "my-api" in md

    def test_contains_commit_subject(self):
        md = render_markdown([_repo_group()])
        assert "add login" in md

    def test_no_commits_message(self):
        empty_group = RepoGroup(repo_name="empty", groups=[])
        md = render_markdown([empty_group])
        # Total commits is 0, so we get the no-commits message
        # But we still have a repo group, so it won't trigger no commits
        # Test with truly empty
        md2 = render_markdown([])
        assert "No commits" in md2

    def test_show_hashes(self):
        md = render_markdown([_repo_group()], show_hashes=True)
        assert "abc1234" in md

    def test_hide_hashes_by_default(self):
        md = render_markdown([_repo_group()], show_hashes=False)
        assert "`abc1234`" not in md

    def test_ai_summary_included(self):
        md = render_markdown(
            [_repo_group()],
            ai_summary="I worked on login features today.",
        )
        assert "AI Summary" in md
        assert "login features" in md

    def test_ai_summary_absent(self):
        md = render_markdown([_repo_group()], ai_summary=None)
        assert "AI Summary" not in md

    def test_multiple_repos(self):
        rg1 = _repo_group(name="api")
        rg2 = _repo_group(name="frontend")
        md = render_markdown([rg1, rg2])
        assert "api" in md
        assert "frontend" in md

    def test_multiple_commit_types(self):
        groups = [
            CommitGroup(
                key="feat", label="Features", emoji="✨",
                commits=[_commit("feat: add login")],
            ),
            CommitGroup(
                key="fix", label="Bug Fixes", emoji="🐛",
                commits=[_commit("fix: resolve crash")],
            ),
        ]
        rg = _repo_group(groups=groups)
        md = render_markdown([rg])
        assert "Features" in md
        assert "Bug Fixes" in md
        assert "add login" in md
        assert "resolve crash" in md
