---
name: import
description: Route Raptor Markdown-to-JSON, JSON-to-SQLite, and future JSON-to-Dolt imports.
metadata:
  version: 1.0.0
---

# Raptor Import

## Step 1 — Verify the runtime

Read and execute `../runtime-preflight.md`. If either check fails, read `references/installation-and-troubleshooting.md` and stop.

Select only the reference matching the requested source and target:

- Markdown → JSON: read `references/markdown-json.md`.
- JSON → SQLite: read `references/json-sqlite.md`.
- JSON → Dolt: read `references/json-dolt.md`.

For Markdown → JSON and JSON → SQLite, use the A3 Agent Runner to invoke the focused agent named by the selected reference with the user's validated parameters. Return only its fenced standard envelope. JSON → Dolt remains unsupported.

For Python or Pydantic setup failures, read `references/installation-and-troubleshooting.md`.
