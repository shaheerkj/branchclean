# GitClean

A CLI tool that analyzes Git repositories for stale, merged, and orphaned branches, then helps you clean them up interactively.

## Install

```bash
pip install branchclean
```

## Usage

### Scan branches

```bash
# Scan current repo
gitclean scan

# Custom staleness threshold
gitclean scan --stale-days 30

# JSON output
gitclean scan --json

# Scan all repos in a directory
gitclean scan --dir ~/projects --multi
```

### Clean branches

```bash
# Interactive cleanup
gitclean clean

# Preview what would be deleted
gitclean clean --dry-run

# Skip prompts (use with caution)
gitclean clean --force
```

### Configuration

Create a `.gitcleanrc` file in your repo root or home directory:

```json
{
  "trunk": "main",
  "stale_days": 60,
  "protected_patterns": ["release/*", "hotfix/*"],
  "include_remote": true
}
```

View resolved config:

```bash
gitclean config
```

## Branch Categories

| Category    | Meaning                              | Color  |
| ----------- | ------------------------------------ | ------ |
| **merged**  | Already merged into trunk            | Green  |
| **orphaned**| Upstream tracking branch is gone     | Yellow |
| **stale**   | No commits in N days (default: 90)   | Red    |
| **active**  | Everything else                      | Dim    |

## Requirements

- Python 3.10+
- Git

## License

MIT
