"""Tests for multi-repository parsing, subdirectory resolution, and error handling."""

import os
import shutil
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

from standup.git_parser import parse_commits, parse_multiple_repos, Commit


# ---------------------------------------------------------------------------
# Mocked tests (simulated paths)
# ---------------------------------------------------------------------------

def test_multi_repo_partial_success():
    """Verify parse_multiple_repos returns commits from valid repos and records errors for invalid ones."""
    mock_commits = [
        Commit(
            hash="abc1234",
            author="User",
            date=datetime(2026, 7, 6, 12, 0, 0),
            subject="feat: test",
            body="",
            branch="main",
            repo_name="valid-repo"
        )
    ]

    def mock_parse(path, **kwargs):
        if "succeeded" in str(path):
            return mock_commits
        raise FileNotFoundError(f"Directory {path} not found")

    with patch("standup.git_parser._get_repo_root", side_effect=lambda p: p), \
         patch("standup.git_parser.parse_commits", side_effect=mock_parse):
        commits, errors = parse_multiple_repos(
            ["/path/to/succeeded", "/path/to/failed"],
            since="yesterday",
            author="User"
        )

        assert len(commits) == 1
        assert commits[0].repo_name == "valid-repo"
        assert "/path/to/failed" in errors
        assert "not found" in errors["/path/to/failed"]
        assert "/path/to/succeeded" not in errors


def test_multi_repo_all_failed():
    """Verify parse_multiple_repos collects all errors when all repos fail."""
    def mock_parse(path, **kwargs):
        raise RuntimeError(f"Git error in {path}")

    with patch("standup.git_parser._get_repo_root", side_effect=lambda p: p), \
         patch("standup.git_parser.parse_commits", side_effect=mock_parse):
        commits, errors = parse_multiple_repos(
            ["/path/to/repo1", "/path/to/repo2"],
            since="yesterday",
            author="User"
        )

        assert len(commits) == 0
        assert "/path/to/repo1" in errors
        assert "/path/to/repo2" in errors
        assert "Git error" in errors["/path/to/repo1"]


def test_multi_repo_zero_commits_distinguishable():
    """Verify zero matching commits is successful (no error) and distinguishable from failures."""
    def mock_parse(path, **kwargs):
        if "empty" in str(path):
            return []  # Success but no commits
        raise RuntimeError(f"Git error in {path}")

    with patch("standup.git_parser._get_repo_root", side_effect=lambda p: p), \
         patch("standup.git_parser.parse_commits", side_effect=mock_parse):
        commits, errors = parse_multiple_repos(
            ["/path/to/empty", "/path/to/failed"],
            since="yesterday",
            author="User"
        )

        assert len(commits) == 0
        assert "/path/to/empty" not in errors
        assert "/path/to/failed" in errors


# ---------------------------------------------------------------------------
# Integration tests using isolated temporary Git repositories
# ---------------------------------------------------------------------------

def _init_git_repo(path: Path) -> None:
    """Initialize a git repository at the given path with one commit."""
    git_path = shutil.which("git") or "git"
    # Init repo
    subprocess.run([git_path, "init"], cwd=str(path), capture_output=True, check=True)
    # Configure user
    subprocess.run([git_path, "config", "user.name", "Test User"], cwd=str(path), capture_output=True, check=True)
    subprocess.run([git_path, "config", "user.email", "test@example.com"], cwd=str(path), capture_output=True, check=True)
    # Add dummy file and commit
    dummy = path / "dummy.txt"
    dummy.write_text("hello world", encoding="utf-8")
    subprocess.run([git_path, "add", "dummy.txt"], cwd=str(path), capture_output=True, check=True)
    subprocess.run([git_path, "commit", "-m", "feat: initial commit"], cwd=str(path), capture_output=True, check=True)


def test_git_parser_repo_root(tmp_path):
    """Verify parsing a repository root directly works and returns the correct name."""
    repo_dir = tmp_path / "my-awesome-repo"
    repo_dir.mkdir()
    _init_git_repo(repo_dir)

    commits = parse_commits(repo_dir, since="1 year ago")
    assert len(commits) == 1
    assert commits[0].subject == "feat: initial commit"
    assert commits[0].repo_name == "my-awesome-repo"


def test_git_parser_nested_subdirectory(tmp_path):
    """Verify passing a nested subdirectory resolves to the main repository."""
    repo_dir = tmp_path / "nested-repo"
    repo_dir.mkdir()
    _init_git_repo(repo_dir)

    # Create subdirectories
    sub_dir = repo_dir / "src" / "standup"
    sub_dir.mkdir(parents=True)

    # Parse commits from the nested subdirectory
    commits = parse_commits(sub_dir, since="1 year ago")
    assert len(commits) == 1
    assert commits[0].subject == "feat: initial commit"
    # Repo name must be the top-level repository folder name, not the sub-folder
    assert commits[0].repo_name == "nested-repo"


def test_git_parser_root_and_subdirectory_deduplication(tmp_path):
    """Verify multi-repo parsing deduplicates a repository when both root and subdirs are supplied."""
    repo_dir = tmp_path / "dedup-repo"
    repo_dir.mkdir()
    _init_git_repo(repo_dir)

    sub_dir = repo_dir / "src"
    sub_dir.mkdir()

    # Pass root, subdirectory, and another subdirectory
    sub_dir2 = repo_dir / "tests"
    sub_dir2.mkdir()

    commits, errors = parse_multiple_repos(
        [repo_dir, sub_dir, sub_dir2],
        since="1 year ago"
    )

    # Repository should be processed only once (no duplication of commits)
    assert len(commits) == 1
    assert commits[0].subject == "feat: initial commit"
    assert commits[0].repo_name == "dedup-repo"
    assert len(errors) == 0


def test_git_parser_two_subdirectories_deduplication(tmp_path):
    """Verify multi-repo parsing deduplicates when two different subdirectories of the same repository are passed."""
    repo_dir = tmp_path / "multi-subdir-repo"
    repo_dir.mkdir()
    _init_git_repo(repo_dir)

    sub1 = repo_dir / "subdir1"
    sub1.mkdir()
    sub2 = repo_dir / "subdir2"
    sub2.mkdir()

    commits, errors = parse_multiple_repos(
        [sub1, sub2],
        since="1 year ago"
    )

    assert len(commits) == 1
    assert commits[0].repo_name == "multi-subdir-repo"
    assert len(errors) == 0


def test_git_parser_existing_non_git_directory(tmp_path, monkeypatch):
    """Verify passing a directory that is not inside a Git repo raises a controlled RuntimeError."""
    # Ensure Git repository discovery is capped at the temp directory root
    monkeypatch.setenv(
        "GIT_CEILING_DIRECTORIES",
        str(tmp_path.resolve()),
    )
    # Remove inherited Git context overrides that could redirect repo discovery
    monkeypatch.delenv("GIT_DIR", raising=False)
    monkeypatch.delenv("GIT_WORK_TREE", raising=False)
    monkeypatch.delenv("GIT_COMMON_DIR", raising=False)

    non_git_dir = tmp_path / "plain-folder"
    non_git_dir.mkdir()

    with pytest.raises(RuntimeError) as excinfo:
        parse_commits(non_git_dir)
    assert "Not a git repository" in str(excinfo.value)
    assert str(non_git_dir) in str(excinfo.value)
