"""Tests for git_parser module."""

from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from standup.git_parser import (
    Commit,
    parse_commits,
    _extract_branch,
    FIELD_SEP,
    RECORD_SEP,
)


# ---------------------------------------------------------------------------
# Commit dataclass tests
# ---------------------------------------------------------------------------

class TestCommit:
    """Test the Commit dataclass properties."""

    def _make_commit(self, subject: str = "feat: add login", **kwargs) -> Commit:
        defaults = dict(
            hash="abc1234567890",
            author="Test User",
            date=datetime(2026, 7, 6, 10, 0, 0),
            subject=subject,
            body="",
            branch="main",
            repo_name="my-repo",
        )
        defaults.update(kwargs)
        return Commit(**defaults)

    def test_short_hash(self):
        c = self._make_commit(hash="abcdef1234567")
        assert c.short_hash == "abcdef1"

    def test_commit_type_feat(self):
        c = self._make_commit(subject="feat: add new feature")
        assert c.commit_type == "feat"

    def test_commit_type_fix(self):
        c = self._make_commit(subject="fix(auth): resolve token bug")
        assert c.commit_type == "fix"

    def test_commit_type_breaking(self):
        c = self._make_commit(subject="feat!: breaking change")
        assert c.commit_type == "feat"

    def test_commit_type_scoped(self):
        c = self._make_commit(subject="refactor(core): clean up utils")
        assert c.commit_type == "refactor"

    def test_commit_type_other(self):
        c = self._make_commit(subject="Update README")
        assert c.commit_type == "other"

    def test_clean_subject_strips_prefix(self):
        c = self._make_commit(subject="feat(ui): add dark mode toggle")
        assert c.clean_subject == "add dark mode toggle"

    def test_clean_subject_no_prefix(self):
        c = self._make_commit(subject="Update dependencies")
        assert c.clean_subject == "Update dependencies"


# ---------------------------------------------------------------------------
# Branch extraction tests
# ---------------------------------------------------------------------------

class TestExtractBranch:
    """Test branch name extraction from git refs."""

    def test_head_arrow(self):
        assert _extract_branch("HEAD -> main") == "main"

    def test_head_arrow_with_origin(self):
        assert _extract_branch("HEAD -> develop, origin/develop") == "develop"

    def test_origin_only(self):
        assert _extract_branch("origin/feature/login") == "feature/login"

    def test_empty_string(self):
        assert _extract_branch("") == "unknown"

    def test_tag_skipped(self):
        assert _extract_branch("tag: v1.0.0, main") == "main"


# ---------------------------------------------------------------------------
# parse_commits tests (with mocked subprocess)
# ---------------------------------------------------------------------------

class TestParseCommits:
    """Test git log parsing with mocked subprocess."""

    def _mock_git_output(self, *commits_data) -> str:
        """Build a mock git log output string."""
        records = []
        for data in commits_data:
            record = FIELD_SEP.join([
                data.get("hash", "abc1234"),
                data.get("author", "Test User"),
                data.get("date", "2026-07-06T10:00:00+03:00"),
                data.get("subject", "feat: test commit"),
                data.get("body", ""),
                data.get("refs", "HEAD -> main"),
            ])
            records.append(RECORD_SEP + record)
        return "".join(records)

    @patch("standup.git_parser._get_repo_root", side_effect=lambda p: p)
    @patch("standup.git_parser.subprocess.run")
    @patch("standup.git_parser.Path.is_dir", return_value=True)
    def test_parse_single_commit(self, mock_isdir, mock_run, mock_get_root):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = self._mock_git_output(
            {"hash": "abcdef1234567", "subject": "feat: add login page"}
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        commits = parse_commits("/fake/repo", since="yesterday", author="Test")

        assert len(commits) == 1
        assert commits[0].subject == "feat: add login page"
        assert commits[0].short_hash == "abcdef1"

    @patch("standup.git_parser._get_repo_root", side_effect=lambda p: p)
    @patch("standup.git_parser.subprocess.run")
    @patch("standup.git_parser.Path.is_dir", return_value=True)
    def test_parse_multiple_commits(self, mock_isdir, mock_run, mock_get_root):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = self._mock_git_output(
            {"hash": "aaa1111", "subject": "feat: first", "date": "2026-07-06T10:00:00+03:00"},
            {"hash": "bbb2222", "subject": "fix: second", "date": "2026-07-06T09:00:00+03:00"},
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        commits = parse_commits("/fake/repo", since="yesterday", author="Test")

        assert len(commits) == 2
        # Should be sorted by date descending
        assert commits[0].subject == "feat: first"
        assert commits[1].subject == "fix: second"

    @patch("standup.git_parser._get_repo_root", side_effect=lambda p: p)
    @patch("standup.git_parser.subprocess.run")
    @patch("standup.git_parser.Path.is_dir", return_value=True)
    def test_empty_output(self, mock_isdir, mock_run, mock_get_root):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        commits = parse_commits("/fake/repo", since="yesterday", author="Test")
        assert commits == []

    def test_nonexistent_repo(self):
        with pytest.raises(FileNotFoundError):
            parse_commits("/this/path/does/not/exist/at/all")
