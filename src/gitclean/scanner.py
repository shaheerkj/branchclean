"""Branch scanning and analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from gitclean import git
from gitclean.config import Config
from gitclean.models import Branch, ScanResult


def _parse_date(raw: str) -> datetime | None:
    """Parse a git ISO date string into a timezone-aware datetime."""
    raw = raw.strip()
    if not raw:
        return None
    # git outputs like "2024-06-15 10:23:45 +0200"
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        # Fallback: try without tz
        try:
            return datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return None


def scan_repo(repo: Path, config: Config) -> ScanResult:
    """Scan a single repository and return a ScanResult."""
    trunk = config.trunk or git.get_trunk_branch(repo)
    cur = git.current_branch(repo)
    merged = git.merged_branches(repo, trunk)
    gone = git.gone_branches(repo)

    branches: list[Branch] = []

    # Local branches
    for info in git.list_local_branches(repo):
        name = info["name"]
        if name == trunk or name == cur:
            continue
        if config.is_protected(name):
            continue
        branches.append(
            Branch(
                name=name,
                commit_date=_parse_date(info["commit_date"]),
                author=info["author"],
                commit_hash=info["commit_hash"],
                is_local=True,
                upstream=info.get("upstream", ""),
                is_merged=name in merged,
                is_gone=name in gone,
            )
        )

    # Remote branches
    if config.include_remote:
        for info in git.list_remote_branches(repo):
            raw_name = info["name"]  # e.g. "origin/feature-x"
            # Strip the remote prefix for display
            parts = raw_name.split("/", 1)
            short_name = parts[1] if len(parts) == 2 else raw_name

            if short_name == trunk or short_name == cur:
                continue
            if config.is_protected(short_name):
                continue

            # Skip if we already have a local branch with the same name
            if any(b.name == short_name and b.is_local for b in branches):
                # Enrich the local branch instead — mark that it has a remote
                for b in branches:
                    if b.name == short_name and b.is_local:
                        b.upstream = b.upstream or raw_name
                        break
                continue

            branches.append(
                Branch(
                    name=raw_name,
                    commit_date=_parse_date(info["commit_date"]),
                    author=info["author"],
                    commit_hash=info["commit_hash"],
                    is_local=False,
                    upstream="",
                    is_merged=short_name in merged,
                    is_gone=False,
                )
            )

    # Sort: merged first, then orphaned, then stale (by date), then active
    def sort_key(b: Branch) -> tuple[int, str]:
        cat = b.category(config.stale_days)
        order = {"merged": 0, "orphaned": 1, "stale": 2, "active": 3, "current": 4}
        return (order.get(cat.value, 5), b.name)

    branches.sort(key=sort_key)

    return ScanResult(
        repo_path=str(repo),
        trunk=trunk,
        current_branch=cur,
        branches=branches,
    )
