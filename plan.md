# GitClean — Stale Branch Cleaner

## Purpose

GitClean is a command-line tool that analyzes Git repositories for stale, merged, and orphaned branches, then provides an interactive workflow to clean them up — both locally and on remotes. It eliminates the tedious manual process of auditing and deleting accumulated branches one by one.

## Problem Statement

Branches accumulate over time across active repositories:

- Feature branches linger long after merging
- Experimental branches are abandoned and forgotten
- Remote-tracking refs stay around after upstream branches are deleted
- `git branch -a` becomes an unreadable wall of text
- Developers avoid cleanup because it's manual, repetitive, and risky (fear of deleting the wrong branch)

There is no single tool that scans, classifies, and interactively cleans branches end-to-end.

---

## Scope

### In Scope

- Local branch analysis (merged status, staleness, authorship)
- Remote branch analysis (same criteria, via remote refs)
- Interactive selection of branches to delete
- Batch deletion of selected branches (local and/or remote)
- Dry-run mode (preview without deleting)
- Multi-repo scanning (scan all repos in a parent directory)
- Configurable staleness threshold
- Protection rules (never offer to delete certain branch patterns)
- Clear, color-coded terminal output

### Out of Scope (for now)

- GitHub/GitLab API integration (PR cleanup, protected branch awareness via API)
- CI/CD pipeline integration
- GUI / web interface
- Modifying or rebasing branches
- Anything that isn't branch cleanup

---

## Core Features

### 1. Branch Analysis (`gitclean scan`)

Scan a repository and produce a structured report of all branches.

**For each branch, determine:**

| Field              | Source                                         |
| ------------------ | ---------------------------------------------- |
| Name               | `git for-each-ref`                             |
| Type               | Local / remote-tracking                        |
| Merged into trunk  | `git branch --merged <trunk>`                  |
| Last commit date   | `git log -1 --format=%ci`                      |
| Last commit author | `git log -1 --format=%an`                      |
| Days since update  | Computed from last commit date                 |
| Stale?             | Days since update > configured threshold       |
| Has remote?        | Whether a local branch tracks a remote         |
| Orphaned tracking? | Remote-tracking ref whose upstream is gone      |

**Default trunk detection:** Automatically detect `main` or `master` (or allow override via flag/config).

**Output format:** Color-coded table in the terminal. Optional `--json` flag for machine-readable output.

### 2. Interactive Cleanup (`gitclean clean`)

Present branches that are candidates for deletion, grouped by category:

1. **Merged branches** — already merged into trunk, safe to delete
2. **Stale branches** — no commits in N days (default: 90), not merged
3. **Orphaned tracking refs** — remote-tracking branches whose upstream no longer exists

For each category, the user can:

- Select individual branches to delete
- Select all in the category
- Skip the category

For each selected branch, delete:

- Local branch (`git branch -d` for merged, `git branch -D` if forced)
- Remote branch (`git push origin --delete <branch>`) if applicable
- Both

### 3. Dry-Run Mode (`--dry-run`)

All commands support a `--dry-run` flag that prints exactly what *would* be deleted without executing anything. This is the default for destructive operations until the user confirms.

### 4. Multi-Repo Mode (`gitclean scan --dir <path>`)

Scan all Git repositories found under a given directory. Useful for developers who keep multiple projects in a workspace folder.

- Recursively discover `.git` directories
- Run the scan for each repository
- Aggregate results in a summary

### 5. Configuration (`.gitcleanrc` or CLI flags)

Configurable via a dotfile in the repo root or home directory, overridable by CLI flags.

| Setting              | Default       | Description                                            |
| -------------------- | ------------- | ------------------------------------------------------ |
| `trunk`              | auto-detect   | Name of the main branch (`main`, `master`, custom)     |
| `stale_days`         | 90            | Days of inactivity before a branch is considered stale |
| `protected_patterns` | `[]`          | Glob patterns for branches that should never be listed (e.g., `release/*`, `hotfix/*`) |
| `default_action`     | `prompt`      | What to do with candidates: `prompt`, `dry-run`, `auto`|
| `include_remote`     | `true`        | Whether to include remote branches in scan/clean       |

---

## CLI Interface

```
gitclean <command> [options]

Commands:
  scan       Analyze branches and display a report
  clean      Interactively delete stale/merged branches
  config     Show resolved configuration

Options (global):
  --dir <path>        Target directory (default: current directory)
  --trunk <branch>    Override trunk branch name
  --stale-days <n>    Override staleness threshold
  --dry-run           Preview actions without executing
  --json              Output in JSON format
  --no-color          Disable colored output
  --force             Skip confirmation prompts
  --verbose           Show detailed git commands being run
  --version           Show version
  --help              Show help
```

### Example Usage

```bash
# Scan current repo
gitclean scan

# Scan with custom staleness threshold
gitclean scan --stale-days 30

# Interactive cleanup
gitclean clean

# Preview what would be deleted
gitclean clean --dry-run

# Scan all repos in a workspace folder
gitclean scan --dir ~/projects

# Force-clean merged branches, no prompts
gitclean clean --force
```

---

## Technical Design

### Language: Python 3.10+

**Rationale:**
- Excellent CLI libraries (`click` or `typer`)
- `subprocess` for git commands is straightforward
- Rich terminal output via `rich` library
- Easy to distribute via `pip` / `pipx`

### Dependencies

| Package  | Purpose                                  |
| -------- | ---------------------------------------- |
| `typer`  | CLI framework (type-hint driven)         |
| `rich`   | Color-coded tables, prompts, spinners    |

Minimal dependency footprint. Git itself is the only external requirement.

### Project Structure

```
GitClean/
├── plan.md
├── pyproject.toml
├── README.md
├── src/
│   └── gitclean/
│       ├── __init__.py
│       ├── cli.py          # CLI entry point, command definitions
│       ├── scanner.py      # Branch analysis logic
│       ├── cleaner.py      # Branch deletion logic
│       ├── config.py       # Configuration loading & resolution
│       ├── git.py          # Low-level git command wrappers
│       └── models.py       # Data classes for branches, scan results
└── tests/
    ├── test_scanner.py
    ├── test_cleaner.py
    ├── test_config.py
    └── test_git.py
```

### Git Interaction

All git operations go through a thin wrapper (`git.py`) that:

- Runs `git` commands via `subprocess.run`
- Captures stdout/stderr
- Raises typed exceptions on failure
- Supports dry-run mode (log the command, don't execute)

No git library (e.g., `gitpython`) — direct subprocess calls are simpler, more transparent, and have no additional dependencies.

---

## Implementation Phases

### Phase 1 — Foundation
- Project scaffolding (`pyproject.toml`, src layout)
- Git wrapper module
- Branch data models
- Basic scan command (local branches only)

### Phase 2 — Full Scan
- Remote branch scanning
- Merge detection
- Staleness calculation
- Rich table output for scan results

### Phase 3 — Interactive Cleanup
- Branch categorization (merged / stale / orphaned)
- Interactive prompts for selection
- Local and remote branch deletion
- Dry-run mode

### Phase 4 — Configuration & Multi-Repo
- `.gitcleanrc` loading
- Protected branch patterns
- Multi-repo directory scanning
- Aggregated output

### Phase 5 — Polish
- `--json` output
- `--verbose` mode
- Error handling edge cases (detached HEAD, bare repos, no remote)
- README with usage examples
- `pipx` installable distribution

---

## Success Criteria

- Running `gitclean scan` in a repo with 20+ branches produces a clear, categorized report in under 2 seconds
- Running `gitclean clean` safely deletes selected branches with zero data loss
- Dry-run mode never executes any destructive git command
- Protected branch patterns are always respected
- The tool works on Windows, macOS, and Linux
