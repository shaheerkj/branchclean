"""Data models for BranchClean."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class BranchCategory(Enum):
    MERGED = "merged"
    STALE = "stale"
    ORPHANED = "orphaned"
    ACTIVE = "active"
    CURRENT = "current"


@dataclass
class Branch:
    name: str
    commit_date: datetime | None
    author: str
    commit_hash: str
    is_local: bool
    upstream: str = ""
    is_merged: bool = False
    is_gone: bool = False  # upstream tracking ref is gone

    @property
    def days_since_update(self) -> int | None:
        if self.commit_date is None:
            return None
        delta = datetime.now(timezone.utc) - self.commit_date
        return delta.days

    def category(self, stale_days: int) -> BranchCategory:
        if self.is_merged:
            return BranchCategory.MERGED
        if self.is_gone:
            return BranchCategory.ORPHANED
        days = self.days_since_update
        if days is not None and days > stale_days:
            return BranchCategory.STALE
        return BranchCategory.ACTIVE


@dataclass
class ScanResult:
    repo_path: str
    trunk: str
    current_branch: str
    branches: list[Branch] = field(default_factory=list)

    @property
    def merged(self) -> list[Branch]:
        return [b for b in self.branches if b.is_merged and b.name != self.trunk]

    @property
    def orphaned(self) -> list[Branch]:
        return [b for b in self.branches if b.is_gone]

    def stale(self, stale_days: int) -> list[Branch]:
        return [
            b
            for b in self.branches
            if not b.is_merged
            and not b.is_gone
            and b.days_since_update is not None
            and b.days_since_update > stale_days
        ]

    @property
    def active(self) -> list[Branch]:
        return [
            b
            for b in self.branches
            if not b.is_merged and not b.is_gone and b.name != self.trunk
        ]
