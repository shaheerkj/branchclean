# Packaging & Publishing

## Package Format

BranchClean uses the modern Python packaging standard defined in `pyproject.toml` (PEP 517/518). This single file replaces the old `setup.py` + `setup.cfg` + `MANIFEST.in` combination.

The build backend is [Hatchling](https://hatch.pypa.io/latest/), a fast, standards-compliant builder.

### Key sections in `pyproject.toml`

**`[build-system]`** — tells pip how to build the package:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**`[project]`** — package metadata surfaced on PyPI:
```toml
name = "branchclean"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["typer>=0.9.0", "rich>=13.0.0"]
```

**`[project.scripts]`** — the CLI entry point:
```toml
[project.scripts]
branchclean = "branchclean.cli:app"
```
This tells pip to create a `branchclean` executable on the system PATH that calls the `app` object in `branchclean/cli.py`.

**`[tool.hatch.build.targets.wheel]`** — tells Hatchling which directory to package:
```toml
packages = ["src/branchclean"]
```

## `src/` Layout

The source code lives under `src/branchclean/` rather than directly in `branchclean/`. This means the local directory is never accidentally imported — only the *installed* package is. This catches import issues early and makes the development environment behave identically to what users get after `pip install`.

## Building

```bash
python -m build
```

Produces two files in `dist/`:

| File | Type | Purpose |
|---|---|---|
| `branchclean-0.1.0-py3-none-any.whl` | Wheel | Pre-built, pip installs this by default |
| `branchclean-0.1.0.tar.gz` | Source dist | Fallback, compiled on user's machine |

The wheel name `py3-none-any` means: pure Python 3, no C extensions, any platform. It works on Windows, macOS, and Linux without recompilation.

## Publishing to PyPI

```bash
pip install twine
twine upload dist/*
```

Twine validates the packages, then uploads them to PyPI over HTTPS. Authentication uses an API token (not your account password):

- **Username:** `__token__` (literal string)
- **Password:** your API token starting with `pypi-`

API tokens are generated at https://pypi.org/manage/account/token/. An account-scoped token works for initial upload; after the project exists you can create a project-scoped token with narrower permissions.

After upload, the package is available at:
```
https://pypi.org/project/branchclean/
```

And installable by anyone with:
```bash
pip install branchclean
# or, for isolated CLI tool install:
pipx install branchclean
```

## GitHub Release

A GitHub Release was created with:
```bash
gh release create v0.1.0 --title "v0.1.0" --notes-file .release-notes.md
```

This:
1. Tags the current `HEAD` commit as `v0.1.0`
2. Creates a Release page on the repo at `/releases/tag/v0.1.0`
3. Shows a "Latest" badge on the repo homepage

GitHub Releases are separate from PyPI — PyPI is for `pip install`, GitHub is for source browsing and changelog tracking. For open-source projects it's standard to keep both in sync.

## Versioning

The version is defined once in `src/branchclean/__init__.py`:
```python
__version__ = "0.1.0"
```

And referenced in `pyproject.toml`:
```toml
version = "0.1.0"
```

For future releases: bump both, rebuild (`python -m build`), upload (`twine upload dist/*`), and create a new GitHub release.
