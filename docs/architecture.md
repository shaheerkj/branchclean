# Architecture Overview

BranchClean is organized into six modules, each with a single responsibility. They form a layered stack where higher layers depend on lower ones but not the reverse.

```
cli.py          ← user interface, commands
  ├── scanner.py    ← branch analysis
  ├── cleaner.py    ← deletion logic
  └── config.py     ← settings

scanner.py / cleaner.py
  └── git.py        ← all git subprocess calls

scanner.py / cleaner.py / cli.py
  └── models.py     ← shared data classes
```

## Project Structure

```
src/branchclean/
├── __init__.py    # package version
├── git.py         # all git operations (subprocess)
├── models.py      # Branch and ScanResult dataclasses
├── config.py      # .branchcleanrc loading + CLI override merging
├── scanner.py     # branch analysis: merged / stale / orphaned
├── cleaner.py     # interactive deletion with dry-run support
└── cli.py         # typer CLI: scan, clean, config commands
```

The `src/` layout is a Python best practice — it forces the installed package to be used rather than the local source directory, preventing subtle import bugs during development.

## Data Flow

```
User runs: branchclean scan
         │
         ▼
      cli.py
   resolves repo path
   loads config
         │
         ▼
     scanner.py
   calls git.py functions
   builds Branch objects
   returns ScanResult
         │
         ▼
      cli.py
   renders Rich table
```

```
User runs: branchclean clean
         │
         ▼
      cli.py
   resolves repo path
   loads config
         │
         ▼
     scanner.py → ScanResult
         │
         ▼
     cleaner.py
   groups branches by category
   prompts user for selection
   calls git.py delete functions
```
