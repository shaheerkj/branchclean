"""Configuration loading and resolution for GitClean."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


_CONFIG_FILENAME = ".gitcleanrc"


@dataclass
class Config:
    trunk: str | None = None  # None means auto-detect
    stale_days: int = 90
    protected_patterns: list[str] = field(default_factory=list)
    include_remote: bool = True

    def is_protected(self, branch_name: str) -> bool:
        """Check if a branch name matches any protected pattern."""
        from fnmatch import fnmatch

        return any(fnmatch(branch_name, pat) for pat in self.protected_patterns)


def load_config(repo: Path | None = None) -> Config:
    """Load config by merging home-level and repo-level .gitcleanrc files.

    Repo-level settings override home-level settings.
    """
    config = Config()

    # Home-level config
    home_rc = Path.home() / _CONFIG_FILENAME
    if home_rc.is_file():
        _merge(config, _read(home_rc))

    # Repo-level config
    if repo is not None:
        repo_rc = repo / _CONFIG_FILENAME
        if repo_rc.is_file():
            _merge(config, _read(repo_rc))

    return config


def _read(path: Path) -> dict:
    """Read a JSON config file."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    return json.loads(text)


def _merge(config: Config, data: dict) -> None:
    """Apply values from *data* onto *config*."""
    if "trunk" in data:
        config.trunk = data["trunk"]
    if "stale_days" in data:
        config.stale_days = int(data["stale_days"])
    if "protected_patterns" in data:
        config.protected_patterns = list(data["protected_patterns"])
    if "include_remote" in data:
        config.include_remote = bool(data["include_remote"])
