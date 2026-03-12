"""CLI entry point for GitClean."""

from __future__ import annotations

import json as json_mod
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from gitclean import __version__, git
from gitclean.cleaner import clean_interactive
from gitclean.config import Config, load_config
from gitclean.models import BranchCategory
from gitclean.scanner import scan_repo

app = typer.Typer(
    name="gitclean",
    help="Analyze and clean up stale, merged, and orphaned Git branches.",
    no_args_is_help=True,
)
console = Console()

# ── Shared options ──────────────────────────────────────────────────────────


def _resolve_repo(directory: Path) -> Path:
    repo = directory.resolve()
    if not git.is_git_repo(repo):
        console.print(f"[red]Error:[/red] {repo} is not a git repository.")
        raise typer.Exit(1)
    return repo


def _build_config(
    trunk: str | None,
    stale_days: int,
    include_remote: bool,
    repo: Path,
) -> Config:
    config = load_config(repo)
    if trunk is not None:
        config.trunk = trunk
    if stale_days != 90:
        config.stale_days = stale_days
    config.include_remote = include_remote
    return config


# ── Commands ────────────────────────────────────────────────────────────────


_CATEGORY_STYLES = {
    BranchCategory.MERGED: "green",
    BranchCategory.ORPHANED: "yellow",
    BranchCategory.STALE: "red",
    BranchCategory.ACTIVE: "dim",
    BranchCategory.CURRENT: "cyan",
}


@app.command()
def scan(
    directory: Path = typer.Option(
        ".", "--dir", "-d", help="Target repository or parent directory."
    ),
    trunk: Optional[str] = typer.Option(
        None, "--trunk", "-t", help="Override trunk branch name."
    ),
    stale_days: int = typer.Option(
        90, "--stale-days", "-s", help="Days of inactivity before a branch is stale."
    ),
    include_remote: bool = typer.Option(
        True, "--remote/--no-remote", help="Include remote-tracking branches."
    ),
    output_json: bool = typer.Option(
        False, "--json", "-j", help="Output results as JSON."
    ),
    multi: bool = typer.Option(
        False, "--multi", "-m", help="Scan all repos under the directory."
    ),
) -> None:
    """Analyze branches and display a report."""
    repos: list[Path] = []
    if multi:
        repos = git.discover_repos(directory.resolve())
        if not repos:
            console.print("[yellow]No git repositories found.[/yellow]")
            raise typer.Exit(0)
    else:
        repos = [_resolve_repo(directory)]

    all_results = []
    for repo in repos:
        config = _build_config(trunk, stale_days, include_remote, repo)
        result = scan_repo(repo, config)
        all_results.append(result)

        if output_json:
            continue

        # Print header
        console.print(f"\n[bold]Repository:[/bold] {result.repo_path}")
        console.print(f"[bold]Trunk:[/bold] {result.trunk}  |  [bold]Current:[/bold] {result.current_branch}")

        if not result.branches:
            console.print("[green]  No cleanup candidates found.[/green]")
            continue

        table = Table(show_header=True, header_style="bold")
        table.add_column("Branch", style="bold")
        table.add_column("Category")
        table.add_column("Type")
        table.add_column("Age (days)", justify="right")
        table.add_column("Author")
        table.add_column("Commit")

        for b in result.branches:
            cat = b.category(config.stale_days)
            style = _CATEGORY_STYLES.get(cat, "")
            days = str(b.days_since_update) if b.days_since_update is not None else "-"
            loc = "local" if b.is_local else "remote"
            table.add_row(
                b.name,
                f"[{style}]{cat.value}[/{style}]",
                loc,
                days,
                b.author,
                b.commit_hash,
            )

        console.print(table)

        # Summary line
        merged_count = len(result.merged)
        orphaned_count = len(result.orphaned)
        stale_count = len(result.stale(config.stale_days))
        console.print(
            f"  [green]{merged_count} merged[/green]  "
            f"[yellow]{orphaned_count} orphaned[/yellow]  "
            f"[red]{stale_count} stale[/red]  "
            f"[dim]{len(result.active)} active[/dim]"
        )

    if output_json:
        data = []
        for r in all_results:
            data.append(
                {
                    "repo": r.repo_path,
                    "trunk": r.trunk,
                    "current_branch": r.current_branch,
                    "branches": [
                        {
                            "name": b.name,
                            "category": b.category(stale_days).value,
                            "is_local": b.is_local,
                            "days_since_update": b.days_since_update,
                            "author": b.author,
                            "commit_hash": b.commit_hash,
                        }
                        for b in r.branches
                    ],
                }
            )
        console.print_json(json_mod.dumps(data, indent=2))


@app.command()
def clean(
    directory: Path = typer.Option(
        ".", "--dir", "-d", help="Target repository directory."
    ),
    trunk: Optional[str] = typer.Option(
        None, "--trunk", "-t", help="Override trunk branch name."
    ),
    stale_days: int = typer.Option(
        90, "--stale-days", "-s", help="Days of inactivity before a branch is stale."
    ),
    include_remote: bool = typer.Option(
        True, "--remote/--no-remote", help="Include remote-tracking branches."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Preview deletions without executing."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip all confirmation prompts."
    ),
) -> None:
    """Interactively delete stale, merged, and orphaned branches."""
    repo = _resolve_repo(directory)
    config = _build_config(trunk, stale_days, include_remote, repo)
    result = scan_repo(repo, config)

    console.print(f"\n[bold]Repository:[/bold] {result.repo_path}")
    console.print(f"[bold]Trunk:[/bold] {result.trunk}  |  [bold]Current:[/bold] {result.current_branch}")

    clean_interactive(
        result,
        repo,
        stale_days=config.stale_days,
        dry_run=dry_run,
        force=force,
    )


@app.command()
def config(
    directory: Path = typer.Option(
        ".", "--dir", "-d", help="Repository to show config for."
    ),
) -> None:
    """Show the resolved configuration."""
    repo = directory.resolve()
    cfg = load_config(repo)
    console.print("[bold]Resolved configuration:[/bold]")
    console.print(f"  trunk:              {cfg.trunk or '(auto-detect)'}")
    console.print(f"  stale_days:         {cfg.stale_days}")
    console.print(f"  protected_patterns: {cfg.protected_patterns or '(none)'}")
    console.print(f"  include_remote:     {cfg.include_remote}")


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit."
    ),
) -> None:
    if version:
        console.print(f"gitclean {__version__}")
        raise typer.Exit()
