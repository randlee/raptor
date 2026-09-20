---
name: validate
description: Route validation of Raptor Markdown, canonical JSON, SQLite, and future Dolt stores.
metadata:
  version: 1.0.0
---

# Raptor Validate

## Step 1 — Verify the runtime

Read and execute `../runtime-preflight.md`. If either check fails, read `references/installation-and-troubleshooting.md` and stop.

Read only the selected reference: `references/markdown.md`, `references/json.md`, `references/sqlite.md`, or `references/dolt.md`.

For Markdown, JSON, and SQLite, use the A3 Agent Runner to invoke the focused agent named by the selected reference. Dolt retains its structured unsupported result. Read `references/installation-and-troubleshooting.md` only for Python/Pydantic setup failures.
