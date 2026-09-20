# Repository Working Rules

## Mandatory worktree policy

- **Always use `/sc-git-worktree` to create every task, feature, fix, documentation, planning, or release worktree.** Do not create worktrees or task branches manually when the skill is available.
- **Always keep the primary Raptor repository checkout on `develop`.** Never switch the primary checkout to a task branch.
- Perform all task edits, commits, tests, pushes, and PR preparation in the dedicated `/sc-git-worktree` worktree created from `develop`.
- Before starting work, verify that the primary checkout is on `develop` and that the task worktree has the intended branch and base.
- If the primary checkout contains task work or is on another branch, preserve the work first, relocate it to a dedicated `/sc-git-worktree`, then restore the primary checkout to `develop`. Never discard user work to enforce this policy.
- Use the `/sc-git-worktree` update, scan, cleanup, or abort workflows for worktree lifecycle operations.

