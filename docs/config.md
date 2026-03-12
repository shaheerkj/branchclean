# config.py — Configuration System

`config.py` handles loading and merging settings from dotfiles and CLI flags.

## Config Sources (in priority order, lowest to highest)

1. Built-in defaults (hardcoded in the `Config` dataclass)
2. `~/.branchcleanrc` (home directory — global user preferences)
3. `<repo>/.branchcleanrc` (repo root — project-specific overrides)
4. CLI flags (highest priority, always win)

## `Config` Dataclass

```python
@dataclass
class Config:
    trunk: str | None = None        # None means auto-detect
    stale_days: int = 90
    protected_patterns: list[str] = []
    include_remote: bool = True
```

### Fields

| Field                 | Default       | Description |
| --------------------- | ------------- | ----------- |
| `trunk`               | `None`        | Name of the main branch. `None` triggers auto-detection via `git.get_trunk_branch()` |
| `stale_days`          | `90`          | A branch is considered stale if its last commit is older than this many days |
| `protected_patterns`  | `[]`          | Glob patterns (e.g. `release/*`, `hotfix/*`). Matching branches are never shown as candidates |
| `include_remote`      | `True`        | Whether to include remote-tracking branches in scan and clean |

### `is_protected(branch_name)`

Checks a branch name against all `protected_patterns` using Python's `fnmatch`. Returns `True` if any pattern matches. Called for every branch during scanning — matching branches are silently skipped.

## `.branchcleanrc` Format

A plain JSON file:

```json
{
  "trunk": "main",
  "stale_days": 60,
  "protected_patterns": ["release/*", "hotfix/*", "develop"],
  "include_remote": true
}
```

All fields are optional — you only need to specify values you want to override.

## `load_config(repo)` Function

```
1. Create Config with defaults
2. If ~/.branchcleanrc exists → read and merge into Config
3. If <repo>/.branchcleanrc exists → read and merge into Config (overrides home)
4. Return Config
```

The `_merge()` helper only updates fields that are present in the JSON — missing keys are left at their current value, so partial configs work correctly.

CLI flags are applied on top of the loaded config inside `cli.py` after `load_config()` returns.
