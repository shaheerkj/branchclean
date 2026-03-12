"""Branch deletion logic with interactive selection."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from branchclean import git
from branchclean.models import Branch, BranchCategory, ScanResult

console = Console()


def _group_candidates(
    result: ScanResult, stale_days: int
) -> dict[BranchCategory, list[Branch]]:
    """Group deletion candidates by category."""
    groups: dict[BranchCategory, list[Branch]] = {
        BranchCategory.MERGED: [],
        BranchCategory.ORPHANED: [],
        BranchCategory.STALE: [],
    }
    for branch in result.branches:
        cat = branch.category(stale_days)
        if cat in groups:
            groups[cat].append(branch)
    return {k: v for k, v in groups.items() if v}


_CATEGORY_LABELS = {
    BranchCategory.MERGED: "[green]Merged branches[/green] (safe to delete)",
    BranchCategory.ORPHANED: "[yellow]Orphaned branches[/yellow] (upstream gone)",
    BranchCategory.STALE: "[red]Stale branches[/red] (no recent commits)",
}


def clean_interactive(
    result: ScanResult,
    repo: Path,
    *,
    stale_days: int,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    """Interactively select and delete branches. Returns count of deleted branches."""
    groups = _group_candidates(result, stale_days)

    if not groups:
        console.print("[green]No branches to clean up![/green]")
        return 0

    to_delete: list[Branch] = []

    for category, branches in groups.items():
        label = _CATEGORY_LABELS.get(category, category.value)
        console.print(f"\n{label}:")
        for i, b in enumerate(branches, 1):
            loc = "local" if b.is_local else "remote"
            days = b.days_since_update
            age = f"{days}d ago" if days is not None else "unknown"
            console.print(f"  {i}. [bold]{b.name}[/bold]  ({loc}, {age}, {b.author})")

        if force:
            to_delete.extend(branches)
            continue

        console.print()
        response = console.input(
            "  Delete [bold]a[/bold]ll / [bold]n[/bold]one / [bold]s[/bold]elect individually? [a/n/s]: "
        ).strip().lower()

        if response == "a":
            to_delete.extend(branches)
        elif response == "s":
            for b in branches:
                if Confirm.ask(f"  Delete [bold]{b.name}[/bold]?", default=False):
                    to_delete.append(b)
        # 'n' or anything else → skip

    if not to_delete:
        console.print("\n[dim]Nothing selected for deletion.[/dim]")
        return 0

    # Summary before execution
    console.print(f"\n[bold]Will delete {len(to_delete)} branch(es):[/bold]")
    for b in to_delete:
        loc = "local" if b.is_local else "remote"
        console.print(f"  - {b.name} ({loc})")

    if dry_run:
        console.print("\n[yellow][DRY RUN] No branches were deleted.[/yellow]")
        return 0

    if not force:
        if not Confirm.ask("\nProceed?", default=False):
            console.print("[dim]Aborted.[/dim]")
            return 0

    # Execute deletions
    deleted = 0
    for b in to_delete:
        try:
            if b.is_local:
                force_flag = b.category(stale_days) != BranchCategory.MERGED
                git.delete_local_branch(repo, b.name, force=force_flag)
                console.print(f"  [green]✓[/green] Deleted local branch {b.name}")
                # Also delete remote if it has an upstream
                if b.upstream:
                    remote_name = b.upstream.split("/", 1)
                    if len(remote_name) == 2:
                        try:
                            git.delete_remote_branch(
                                repo, remote_name[1], remote=remote_name[0]
                            )
                            console.print(
                                f"  [green]✓[/green] Deleted remote branch {b.upstream}"
                            )
                        except git.GitError:
                            # Remote branch may already be gone
                            pass
            else:
                # Remote-only branch: "origin/feature-x" → remote=origin, branch=feature-x
                parts = b.name.split("/", 1)
                if len(parts) == 2:
                    git.delete_remote_branch(repo, parts[1], remote=parts[0])
                    console.print(f"  [green]✓[/green] Deleted remote branch {b.name}")
            deleted += 1
        except git.GitError as exc:
            console.print(f"  [red]✗[/red] Failed to delete {b.name}: {exc}")

    console.print(f"\n[bold green]Deleted {deleted} branch(es).[/bold green]")
    return deleted
