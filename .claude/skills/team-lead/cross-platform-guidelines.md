# Team-Lead Cross-Platform Assignment Notes

Use this note when assigning implementation work so platform constraints are not lost in the handoff.

## Rule

For Rust work, include:
- `.claude/skills/rust-development/cross-platform-guidelines.md`
- `.claude/skills/rust-development/guidelines.txt`

This file exists so team-lead always has a local, stable reference inside the `team-lead` skill.

## What Team-Lead Must Call Out

- no hardcoded `/tmp/` paths
- no hardcoded `/` or `\\` path separators
- use `Path` / `PathBuf` and `path.join(...)`
- avoid environment-variable tricks that only work on Unix
- avoid tests that assume Unix line endings or filesystem layout

## Assignment Guidance

When the task touches filesystem, temp files, environment variables, CLI paths, sockets, artifact generation, or tests:

1. mention that cross-platform correctness is required
2. attach the Rust cross-platform guideline path explicitly
3. require the assignee to verify the touched code does not introduce Unix-only assumptions

## Installed Rust Reference

Authoritative Rust cross-platform detail lives at:
- `.claude/skills/rust-development/cross-platform-guidelines.md`
