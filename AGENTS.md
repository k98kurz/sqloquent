# Instructions for Agents

## Testing

Before running tests or python scripts, use `source venv/bin/activate`.

Tests use direct Python execution (not pytest):
- Unix: `find tests -name test_*.py -print -exec python {} \;`
- Windows: Run each test file individually (test_*.py)

Tests import from `tests/context.py`, not from the installed package.

## CLI Tool

The `sqloquent` CLI generates models/migrations and manages migrations.

For migration tools, set environment variables:
- `CONNECTION_STRING`: Database connection info
- `MAKE_WITH_CONNSTRING` (optional): Include connection string in generated scaffolds

## Build & Release

Version strings must be updated in sync across:
- `sqloquent/version.py`
- `pyproject.toml`

No automated linting, typechecking, or CI exists. Only the human can build and
release. Do NOT touch the version strings unless explicitly directed by a human.

## git worktrees

Worktrees should be created inside the `.worktrees/` subdirectory (not as sister folders).

Creating: `git worktree add .worktrees/<branch-name> -b <branch-name>`
Listing: `git worktree list`
Removing: `git worktree remove .worktrees/<branch-name> && git branch -d <branch-name>`

## Code Style Guidelines

The code style guidelines are in code_style.md. Read them before editing or
reviewing code.

## Additional findings

If you encounter anything tricky that is likely to trip up future agents, add a
concise entry here and tell your human.
