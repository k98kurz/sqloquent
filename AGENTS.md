# Instructions for Agents

## venv

Before running tests or python scripts, use `source venv/bin/activate`.

## git worktrees

Worktrees should be created inside the `.worktrees/` subdirectory (not as sister folders).

Creating a worktree: `git worktree add .worktrees/<branch-name> -b <branch-name>`

Listing worktrees: `git worktree list`

Removing a worktree:
```bash
git worktree remove .worktrees/<branch-name>
git branch -d <branch-name>
```

## additional findings

If you encounter anything tricky that is likely to trip up future agents, add a
concise entry in AGENTS.md with information helpful for resolving the issue, then
tell your human about the new entry.

