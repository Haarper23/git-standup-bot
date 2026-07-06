"""Git log parser — reads and structures commit data from git repositories.

Runs `git log` via subprocess and parses the output into structured Commit objects.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


# Custom delimiter to safely split git log fields
FIELD_SEP = "§§§"
RECORD_SEP = "†††"

# git log format: hash, author, date (ISO), subject, body, refs
GIT_LOG_FORMAT = FIELD_SEP.join(["%H", "%an", "%aI", "%s", "%b", "%D"])


@dataclass
class Commit:
    """Represents a single parsed git commit."""

    hash: str
    author: str
    date: datetime
    subject: str
    body: str
    branch: str
    repo_name: str

    @property
    def short_hash(self) -> str:
        """Return abbreviated commit hash."""
        return self.hash[:7]

    @property
    def commit_type(self) -> str:
        """Extract conventional commit type (feat, fix, etc.) from subject."""
        match = re.match(r"^(\w+)(?:\(.+?\))?!?:\s", self.subject)
        if match:
            return match.group(1).lower()
        return "other"

    @property
    def clean_subject(self) -> str:
        """Return subject without conventional commit prefix."""
        cleaned = re.sub(r"^\w+(?:\(.+?\))?!?:\s*", "", self.subject)
        return cleaned.strip() or self.subject


def _extract_branch(refs: str) -> str:
    """Extract the most relevant branch name from git refs string.

    Args:
        refs: Raw refs string from git log %D format.

    Returns:
        Branch name or 'unknown'.
    """
    if not refs.strip():
        return "unknown"

    # Look for HEAD -> branch pattern
    head_match = re.search(r"HEAD\s*->\s*([\w/.-]+)", refs)
    if head_match:
        return head_match.group(1)

    # Look for any branch-like ref (skip tags)
    for ref in refs.split(","):
        ref = ref.strip()
        if ref and not ref.startswith("tag:") and ref != "HEAD":
            # Remove origin/ prefix for readability
            ref = re.sub(r"^origin/", "", ref)
            return ref

    return "unknown"


def _get_repo_root(path: Path) -> Path:
    """Get the actual Git repository root using `git rev-parse --show-toplevel`.

    Raises:
        FileNotFoundError: If the path is not a directory.
        RuntimeError: If the path is not inside a git repository.
    """
    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {path}")

    git_path = shutil.which("git") or "git"
    try:
        result = subprocess.run(
            [git_path, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(path),
            timeout=10,
        )  # nosec B603
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Git command timed out checking repo root for {path}")
    except FileNotFoundError:
        raise RuntimeError("Git is not installed or not in PATH")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"Not a git repository: {path} ({stderr})")

    resolved = Path(result.stdout.strip()).resolve()
    return resolved


def _get_current_branch(repo_path: Path) -> str:
    """Get the current branch name of a repository.

    Args:
        repo_path: Path to the git repository.

    Returns:
        Current branch name or 'unknown'.
    """
    try:
        git_path = shutil.which("git") or "git"
        result = subprocess.run(
            [git_path, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(repo_path),
            timeout=10,
        )  # nosec B603
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return "unknown"


def _get_git_user(repo_path: Path) -> str:
    """Get the configured git user name for a repository.

    Args:
        repo_path: Path to the git repository.

    Returns:
        Git user name or empty string.
    """
    try:
        git_path = shutil.which("git") or "git"
        result = subprocess.run(
            [git_path, "config", "user.name"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(repo_path),
            timeout=10,
        )  # nosec B603
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def parse_commits(
    repo_path: str | Path,
    since: str = "yesterday",
    author: str = "",
) -> list[Commit]:
    """Parse git log output into a list of Commit objects.

    Args:
        repo_path: Path to the git repository.
        since: Git-compatible time string (e.g., "yesterday", "3 days ago").
        author: Filter by author name. If empty, uses git config user.name.

    Returns:
        List of Commit objects, sorted by date descending.

    Raises:
        FileNotFoundError: If the repo path doesn't exist.
        RuntimeError: If git command fails.
    """
    repo_path = Path(repo_path).resolve()
    resolved_root = _get_repo_root(repo_path)

    # Resolve author
    if not author:
        author = _get_git_user(resolved_root)

    # Build git log command
    # Resolve full git path to avoid partial path issues (B607)
    git_path = shutil.which("git") or "git"
    cmd = [
        git_path, "log",
        f"--since={since}",
        f"--format={RECORD_SEP}{GIT_LOG_FORMAT}",
        "--all",
    ]
    if author:
        cmd.append(f"--author={author}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(resolved_root),
            timeout=30,
        )  # nosec B603
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Git command timed out for {resolved_root}")
    except FileNotFoundError:
        raise RuntimeError("Git is not installed or not in PATH")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        # Empty results are not an error
        if "does not have any commits" in stderr or not stderr:
            return []
        raise RuntimeError(f"Git error in {resolved_root}: {stderr}")

    # Get repo name from resolved repository root directory
    repo_name = resolved_root.name

    # Get current branch as fallback
    current_branch = _get_current_branch(resolved_root)

    # Parse output
    commits: list[Commit] = []
    raw = result.stdout.strip()

    if not raw:
        return []

    records = raw.split(RECORD_SEP)

    for record in records:
        record = record.strip()
        if not record:
            continue

        parts = record.split(FIELD_SEP)
        if len(parts) < 6:
            continue

        hash_val, author_name, date_str, subject, body, refs = parts[:6]

        # Parse ISO date
        try:
            commit_date = datetime.fromisoformat(date_str)
        except ValueError:
            continue

        # Extract branch from refs, fallback to current branch
        branch = _extract_branch(refs)
        if branch == "unknown":
            branch = current_branch

        commits.append(
            Commit(
                hash=hash_val.strip(),
                author=author_name.strip(),
                date=commit_date,
                subject=subject.strip(),
                body=body.strip(),
                branch=branch,
                repo_name=repo_name,
            )
        )

    # Sort by date descending
    commits.sort(key=lambda c: c.date, reverse=True)
    return commits


def parse_multiple_repos(
    repo_paths: list[str | Path],
    since: str = "yesterday",
    author: str = "",
) -> tuple[list[Commit], dict[str, str]]:
    """Parse commits from multiple repositories.

    Args:
        repo_paths: List of paths to git repositories.
        since: Git-compatible time string.
        author: Filter by author name.

    Returns:
        A tuple containing:
            - list[Commit]: Combined list of commits from all succeeded repos, sorted by date descending.
            - dict[str, str]: Dictionary mapping failed repository paths to their error message.
    """
    all_commits: list[Commit] = []
    errors: dict[str, str] = {}
    processed_roots: set[str] = set()

    for path in repo_paths:
        try:
            p = Path(path).resolve()
            resolved_root = _get_repo_root(p)

            # Case-insensitive/platform-aware comparison for Windows path deduplication
            canonical_key = os.path.normcase(str(resolved_root))
            if canonical_key in processed_roots:
                continue
            processed_roots.add(canonical_key)

            commits = parse_commits(resolved_root, since=since, author=author)
            all_commits.extend(commits)
        except (FileNotFoundError, RuntimeError) as e:
            errors[str(path)] = str(e)

    all_commits.sort(key=lambda c: c.date, reverse=True)
    return all_commits, errors
