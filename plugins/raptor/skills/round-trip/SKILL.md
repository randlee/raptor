---
name: round-trip
description: Route Raptor semantic migration round trips while preserving canonical identity and provenance.
metadata:
  version: 1.0.0
---

# Raptor Round Trip

## Step 1 — Verify sc-compose

Run `which sc-compose && sc-compose --version` before any agent delegation and enforce the authoritative range in `../../plugin-manifest.json`. If PATH lookup fails, check `$HOME/.local/bin/sc-compose`, `$HOME/.venvs/sc-compose/bin/sc-compose`, `$(python3 -m site --user-base 2>/dev/null)/bin/sc-compose`, and `/opt/homebrew/bin/sc-compose`. If missing or incompatible, read `references/installation-and-troubleshooting.md` and stop.

## Step 2 — Verify the runtime

Read and execute `../runtime-preflight.md`. If either check fails, read `references/installation-and-troubleshooting.md` and stop.

Read `references/migration.md` for the requested migration, or `references/dolt.md` when Dolt participates.

Use the A3 Agent Runner to invoke `migration-round-trip`. The agent composes the registered A4 scripts with JSON → Markdown rendering. Dolt remains unsupported.
