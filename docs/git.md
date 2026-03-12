# git.py — Git Subprocess Wrapper

`git.py` is the lowest layer. Every interaction with git goes through here. No other module runs git commands directly.

## Core Runner

```python
def _run(args, repo, *, dry_run=False):
    cmd = ["git", "-C", str(repo), *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(cmd, result.returncode, result.stderr)
    return result.stdout
```

The `-C <path>` flag tells git which repository to operate in without needing to `cd` into it. This is what makes multi-repo scanning work — you can point at any repo on disk and run commands against it.

If a command fails, a typed `GitError` exception is raised with the command, return code, and stderr. Callers can catch this specifically rather than dealing with raw subprocess errors.

The `dry_run` flag short-circuits execution entirely — the command is not run, and an empty string is returned. The caller is responsible for logging what would have happened before calling `_run`.

## Key Functions

### `list_local_branches(repo)`

Uses `git for-each-ref` with a custom format to get all local branch metadata in one call:

```
%(refname:short)  %(committerdate:iso)  %(authorname)  %(objectname:short)  %(upstream:short)
```

This returns every branch with its name, last commit date, author, commit hash, and upstream tracking branch — all from a single git invocation, which is much faster than calling `git log` per branch.

### `list_remote_branches(repo)`

Same approach but targeting `refs/remotes/` instead of `refs/heads/`. Skips `HEAD` pointer entries (`origin/HEAD`).

### `merged_branches(repo, trunk)`

```bash
git branch --merged <trunk>
```

Returns every local branch whose tip is reachable from `trunk` — meaning it's already been integrated and is safe to delete.

### `gone_branches(repo)`

```bash
git for-each-ref --format "%(refname:short)%(upstream:track)" refs/heads/
```

Looks for branches where `%(upstream:track)` contains `[gone]`. This means the local branch is tracking a remote branch that no longer exists — a common result of someone else deleting the remote branch after merging a PR.

### `get_trunk_branch(repo)`

Auto-detects the main branch in three steps:
1. Reads `git symbolic-ref refs/remotes/origin/HEAD` (e.g. `refs/remotes/origin/main`) and extracts the last segment
2. Falls back to checking if `main` or `master` exist locally
3. Last resort: returns the currently checked-out branch

### `discover_repos(root)`

Recursively walks a directory tree looking for `.git` folders. When it finds one, it records the parent as a repo and does not recurse further into it. Stops at a configurable max depth (default: 3) to avoid scanning deep into `node_modules` or similar trees.

## Error Handling

All public functions let `GitError` propagate up. The cleaner catches it per-branch and reports the failure without aborting the rest of the cleanup. The CLI lets unexpected errors bubble up to Typer's top-level handler.
