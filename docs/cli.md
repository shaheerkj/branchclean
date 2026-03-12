# cli.py — CLI Commands

`cli.py` is the entry point for everything the user types. It wires together config loading, scanning, and cleaning, then handles all display.

## Framework: Typer

BranchClean uses [Typer](https://typer.tiangolo.com/) — a CLI library that turns type-annotated Python functions into commands with arguments, options, help text, and shell completion, with zero boilerplate.

Each command is a plain function decorated with `@app.command()`. Typer reads the type annotations and default values to build the CLI automatically:

```python
@app.command()
def scan(
    directory: Path = typer.Option(".", "--dir", "-d"),
    stale_days: int = typer.Option(90, "--stale-days", "-s"),
    ...
):
```

This produces `branchclean scan --dir . --stale-days 90` with full `--help` output, type validation, and tab completion.

## Commands

### `branchclean scan`

1. Resolves the repo path (validates it's actually a git repo via `git rev-parse`)
2. Loads and merges config with CLI flags
3. Calls `scanner.scan_repo()` to get a `ScanResult`
4. Renders a Rich table with columns: Branch, Category, Type, Age, Author, Commit
5. Applies color styles per category (`green` = merged, `yellow` = orphaned, `red` = stale, `dim` = active)
6. Prints a summary line: `2 merged  0 orphaned  1 stale  5 active`

**`--multi` flag**: calls `git.discover_repos()` to find all repos under `--dir` and runs the full scan+display loop for each one.

**`--json` flag**: skips the Rich table entirely and serializes all results to JSON via `console.print_json()`. Useful for piping into other tools.

### `branchclean clean`

1. Same repo resolution and config loading as `scan`
2. Calls `scanner.scan_repo()` for the candidate list
3. Passes the result to `cleaner.clean_interactive()` with `dry_run` and `force` flags

### `branchclean config`

Loads the config for the given directory and prints each field. Useful for debugging why a branch isn't showing up (e.g., a protected pattern matching it).

### `--version` / `--help`

Handled by Typer's `@app.callback()`. `--version` prints the version string from `branchclean.__version__` and exits.

## Display: Rich

[Rich](https://rich.readthedocs.io/) handles all terminal output:

- `Table` — the branch report with auto-sized columns
- `Console.print()` — styled text with markup like `[green]text[/green]`
- `Confirm.ask()` — the yes/no confirmation prompt
- `console.print_json()` — pretty-printed, syntax-highlighted JSON

Rich automatically disables colors when output is piped to a file or non-TTY, so `branchclean scan > output.txt` produces clean plain text.

## Helper: `_resolve_repo(directory)`

Validates that the given path is inside a git work-tree by running `git rev-parse --is-inside-work-tree`. If it fails, prints an error and calls `raise typer.Exit(1)` — this exits cleanly without a traceback.

## Entry Point

Registered in `pyproject.toml` as:

```toml
[project.scripts]
branchclean = "branchclean.cli:app"
```

When pip installs the package, it generates a small launcher script on the system PATH that calls `app()`. `app` is the Typer `app` instance — calling it triggers Typer's argument parsing and dispatches to the appropriate command function.
