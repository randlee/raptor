---
name: export
description: Route Raptor SQLite-to-JSON, JSON-to-Markdown, and future Dolt-to-JSON exports.
metadata:
  version: 1.0.0
---

# Raptor Export

## Step 1 — Verify sc-compose for JSON → Markdown

For JSON → Markdown, run `which sc-compose && sc-compose --version` before any agent delegation. Read the authoritative range from `../../plugin-manifest.json`. If PATH lookup fails, check `$HOME/.local/bin/sc-compose`, `$HOME/.venvs/sc-compose/bin/sc-compose`, `$(python3 -m site --user-base 2>/dev/null)/bin/sc-compose`, and `/opt/homebrew/bin/sc-compose`. If missing or incompatible, read `references/installation-and-troubleshooting.md` and stop.

## Step 2 — Verify the runtime

Read and execute `../runtime-preflight.md`. If either check fails, read `references/installation-and-troubleshooting.md` and stop.

Read only the selected reference: `references/sqlite-json.md`, `references/json-markdown.md`, or `references/dolt-json.md`.

Use the A3 Agent Runner to invoke `sqlite-json-export` or `json-markdown-export` with the selected reference's parameters. Dolt → JSON retains its structured unsupported result.
