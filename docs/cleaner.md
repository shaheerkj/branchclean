# cleaner.py — Interactive Deletion

`cleaner.py` takes a `ScanResult`, presents deletion candidates to the user, collects their choices, then executes the deletions.

## `clean_interactive(result, repo, *, stale_days, dry_run, force)`

The single public function.

### Step 1 — Group candidates

```python
groups = {
    BranchCategory.MERGED:   [...],
    BranchCategory.ORPHANED: [...],
    BranchCategory.STALE:    [...],
}
```

Active branches are never deletion candidates — they're excluded entirely. Each candidate branch is classified using `branch.category(stale_days)`.

### Step 2 — Present each group

For each non-empty category, prints a labeled list:

```
Merged branches (safe to delete):
  1. feature/payments  (local, 45d ago, Alice)
  2. fix/typo          (local, 12d ago, Bob)

Delete all / none / select individually? [a/n/s]:
```

User responses:
- `a` → add all branches in this group to the delete list
- `n` (or anything else) → skip this group entirely
- `s` → loop through each branch with an individual yes/no prompt (using Rich's `Confirm.ask`)

If `--force` is set, all groups are selected automatically without any prompting.

### Step 3 — Confirmation summary

Before touching anything, prints the full list of what will be deleted:

```
Will delete 3 branch(es):
  - feature/payments (local)
  - fix/typo (local)
  - origin/old-experiment (remote)
```

Then asks for a final `Proceed? [y/N]` confirmation (skipped with `--force`).

### Step 4 — Dry-run exit

If `--dry-run` is set, the function exits here with a message saying nothing was deleted. No git commands are ever called.

### Step 5 — Execute deletions

For each selected branch:

**Local branch:**
- Uses `git branch -d` for merged branches (safe delete — git refuses if not merged)
- Uses `git branch -D` for stale/orphaned branches (force delete required)
- If the local branch has an upstream tracking ref, also deletes the remote branch (`git push origin --delete <branch>`)

**Remote-only branch** (e.g. `origin/feature-x`):
- Splits on the first `/` to get remote name and branch name
- Calls `git push <remote> --delete <branch>`

Failures on individual branches are caught and reported without aborting the rest of the loop. A summary count of successful deletions is printed at the end.

## Why `-D` for stale branches?

`git branch -d` refuses to delete a branch that isn't fully merged. Stale and orphaned branches may have unmerged commits — the user has explicitly chosen to delete them, so `-D` (force) is appropriate. Merged branches always use `-d` as a safety net even though they're guaranteed to be merged.
