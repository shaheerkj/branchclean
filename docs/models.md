# models.py — Data Classes

`models.py` defines the two core data structures used throughout the application. Every other module either produces or consumes these types.

## `Branch`

Represents a single git branch, local or remote.

```python
@dataclass
class Branch:
    name: str               # branch name (or "origin/feature-x" for remote-only)
    commit_date: datetime   # last commit timestamp (timezone-aware)
    author: str             # last commit author name
    commit_hash: str        # short commit hash
    is_local: bool          # True = local branch, False = remote-only
    upstream: str           # tracking ref, e.g. "origin/feature-x"
    is_merged: bool         # merged into trunk?
    is_gone: bool           # upstream tracking branch no longer exists?
```

### Computed properties

**`days_since_update`** — subtracts `commit_date` from `now(utc)` and returns the number of days. Returns `None` if the date couldn't be parsed.

**`category(stale_days)`** — classifies the branch into one of five categories, checked in priority order:

| Category   | Condition                                         |
| ---------- | ------------------------------------------------- |
| `MERGED`   | `is_merged` is True                               |
| `ORPHANED` | `is_gone` is True (upstream tracking ref gone)    |
| `STALE`    | `days_since_update > stale_days`                  |
| `ACTIVE`   | Everything else (recent, unmerged)                |
| `CURRENT`  | The currently checked-out branch (excluded from candidates) |

Merged takes priority over stale because a branch can be both merged and old — it should be treated as safe to delete (merged), not alarming (stale).

## `BranchCategory`

An enum with values: `MERGED`, `STALE`, `ORPHANED`, `ACTIVE`, `CURRENT`.

Used as keys when grouping candidates in the cleaner and for applying color styles in the CLI table.

## `ScanResult`

Holds the full result of scanning one repository.

```python
@dataclass
class ScanResult:
    repo_path: str          # absolute path to the repo
    trunk: str              # detected or configured trunk branch name
    current_branch: str     # currently checked-out branch
    branches: list[Branch]  # all candidate branches (excludes trunk and current)
```

### Filter properties

| Property          | Returns                                         |
| ----------------- | ----------------------------------------------- |
| `merged`          | Branches with `is_merged=True`                  |
| `orphaned`        | Branches with `is_gone=True`                    |
| `stale(n)`        | Unmerged, non-orphaned branches older than N days |
| `active`          | Everything not merged, not gone, not trunk      |

These are used by `cleaner.py` to group candidates and by `cli.py` to print the summary counts at the bottom of the scan table.
