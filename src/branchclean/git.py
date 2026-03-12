"""Thin wrapper around git subprocess calls."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(Exception):
    """Raised when a git command fails."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"git command failed ({returncode}): {stderr.strip()}")


def _run(
    args: list[str],
    repo: Path,
    *,
    dry_run: bool = False,
    check: bool = True,
) -> str:
    """Run a git command and return stdout.

    If *dry_run* is True the command is not executed and an empty string is
    returned.  The caller is responsible for logging dry-run intentions before
    calling this.
    """
    cmd = ["git", "-C", str(repo), *args]
    if dry_run:
        return ""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise GitError(cmd, result.returncode, result.stderr)
    return result.stdout


def is_git_repo(path: Path) -> bool:
    """Return True if *path* is inside a git work-tree."""
    try:
        _run(["rev-parse", "--is-inside-work-tree"], path)
        return True
    except (GitError, FileNotFoundError):
        return False


def get_trunk_branch(repo: Path) -> str:
    """Auto-detect the trunk branch (main/master) for *repo*."""
    # Check the HEAD reference of origin first
    try:
        ref = _run(["symbolic-ref", "refs/remotes/origin/HEAD"], repo).strip()
        # refs/remotes/origin/main -> main
        return ref.split("/")[-1]
    except GitError:
        pass

    # Fallback: check if main or master exist locally
    branches = _run(["branch", "--list"], repo).strip().splitlines()
    branch_names = {b.strip().lstrip("* ") for b in branches}
    for candidate in ("main", "master"):
        if candidate in branch_names:
            return candidate

    # Last resort — current branch
    return _run(["rev-parse", "--abbrev-ref", "HEAD"], repo).strip()


def list_local_branches(repo: Path) -> list[dict[str, str]]:
    """Return local branch info as a list of dicts.

    Each dict contains: name, commit_date, author, commit_hash, upstream.
    """
    fmt = "%(refname:short)%09%(committerdate:iso)%09%(authorname)%09%(objectname:short)%09%(upstream:short)"
    lines = _run(
        ["for-each-ref", "--format", fmt, "refs/heads/"],
        repo,
    ).strip().splitlines()

    branches: list[dict[str, str]] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        branches.append(
            {
                "name": parts[0],
                "commit_date": parts[1] if len(parts) > 1 else "",
                "author": parts[2] if len(parts) > 2 else "",
                "commit_hash": parts[3] if len(parts) > 3 else "",
                "upstream": parts[4] if len(parts) > 4 else "",
            }
        )
    return branches


def list_remote_branches(repo: Path) -> list[dict[str, str]]:
    """Return remote-tracking branch info as a list of dicts."""
    fmt = "%(refname:short)%09%(committerdate:iso)%09%(authorname)%09%(objectname:short)"
    lines = _run(
        ["for-each-ref", "--format", fmt, "refs/remotes/"],
        repo,
    ).strip().splitlines()

    branches: list[dict[str, str]] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        name = parts[0]
        # Skip HEAD pointer
        if name.endswith("/HEAD"):
            continue
        branches.append(
            {
                "name": name,
                "commit_date": parts[1] if len(parts) > 1 else "",
                "author": parts[2] if len(parts) > 2 else "",
                "commit_hash": parts[3] if len(parts) > 3 else "",
            }
        )
    return branches


def merged_branches(repo: Path, trunk: str) -> set[str]:
    """Return a set of local branch names that are merged into *trunk*."""
    lines = _run(["branch", "--merged", trunk], repo).strip().splitlines()
    result: set[str] = set()
    for line in lines:
        name = line.strip().lstrip("* ")
        if name and name != trunk:
            result.add(name)
    return result


def gone_branches(repo: Path) -> set[str]:
    """Return local branches whose upstream tracking branch is gone."""
    fmt = "%(refname:short)%09%(upstream:track)"
    lines = _run(
        ["for-each-ref", "--format", fmt, "refs/heads/"],
        repo,
    ).strip().splitlines()

    result: set[str] = set()
    for line in lines:
        parts = line.split("\t")
        if len(parts) == 2 and "[gone]" in parts[1]:
            result.add(parts[0])
    return result


def current_branch(repo: Path) -> str:
    """Return the name of the currently checked-out branch."""
    return _run(["rev-parse", "--abbrev-ref", "HEAD"], repo).strip()


def delete_local_branch(
    repo: Path, branch: str, *, force: bool = False, dry_run: bool = False
) -> None:
    """Delete a local branch."""
    flag = "-D" if force else "-d"
    _run(["branch", flag, branch], repo, dry_run=dry_run)


def delete_remote_branch(
    repo: Path, branch: str, *, remote: str = "origin", dry_run: bool = False
) -> None:
    """Delete a remote branch."""
    _run(["push", remote, "--delete", branch], repo, dry_run=dry_run)


def fetch_prune(repo: Path) -> None:
    """Fetch and prune stale remote-tracking refs."""
    _run(["fetch", "--prune"], repo)


def discover_repos(root: Path, *, max_depth: int = 3) -> list[Path]:
    """Recursively find git repositories under *root*."""
    repos: list[Path] = []
    _walk(root, repos, depth=0, max_depth=max_depth)
    return repos


def _walk(path: Path, repos: list[Path], depth: int, max_depth: int) -> None:
    if depth > max_depth:
        return
    try:
        entries = sorted(path.iterdir())
    except PermissionError:
        return
    for entry in entries:
        if entry.is_dir():
            if entry.name == ".git":
                repos.append(path)
                return  # don't recurse into the repo itself
            if not entry.name.startswith("."):
                _walk(entry, repos, depth + 1, max_depth)
