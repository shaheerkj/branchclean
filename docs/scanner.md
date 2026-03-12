# scanner.py — Branch Analysis

`scanner.py` is responsible for collecting all branch data from a repo and producing a `ScanResult`. It sits between `git.py` (raw data) and `cli.py` / `cleaner.py` (consumers).

## `scan_repo(repo, config)` 

The single public function. Takes a repo path and a resolved `Config`, returns a `ScanResult`.

### Step-by-step

**1. Get context**

```python
trunk = config.trunk or git.get_trunk_branch(repo)
cur = git.current_branch(repo)
merged = git.merged_branches(repo, trunk)   # set of names
gone = git.gone_branches(repo)              # set of names
```

The trunk is resolved first — either from config or auto-detected. The merged and gone sets are fetched once and reused for every branch, rather than checking per-branch.

**2. Process local branches**

Loops through `git.list_local_branches()` and for each one:
- Skips it if it's the trunk or currently checked-out branch
- Skips it if `config.is_protected(name)` returns True
- Parses the commit date string into a timezone-aware `datetime`
- Constructs a `Branch` with `is_merged = name in merged` and `is_gone = name in gone`

**3. Process remote branches**

Loops through `git.list_remote_branches()`. Remote branch names come in the form `origin/feature-x`, so the short name (`feature-x`) is extracted for comparison.

For each remote branch:
- Skips trunk and current branch equivalents
- Skips protected patterns
- **If a local branch with the same short name already exists**: enriches that local branch's `upstream` field instead of adding a duplicate entry. This avoids showing the same branch twice.
- Otherwise: adds a remote-only `Branch` with `is_local=False`

**4. Sort**

Branches are sorted so the most actionable ones appear first:

```
merged → orphaned → stale (by date) → active
```

This is done via a `sort_key` function that maps each category to a sort integer.

## Date Parsing

Git outputs dates in ISO format: `2024-06-15 10:23:45 +0200`. The parser handles:
- Full ISO with timezone offset (primary case)
- Truncated ISO without timezone (fallback, assumes UTC)
- Completely unparseable strings (returns `None`)

Timezone-aware datetimes are important because `days_since_update` compares against `datetime.now(timezone.utc)`. Mixing aware and naive datetimes would raise a `TypeError`.
