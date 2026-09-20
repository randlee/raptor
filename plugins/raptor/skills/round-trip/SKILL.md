---
name: round-trip
description: Route Raptor semantic migration round trips while preserving canonical identity and provenance.
metadata:
  version: 1.0.0
---

# Raptor Round Trip

## Step 1 — Verify the runtime

Read and execute `../runtime-preflight.md`. If either check fails, read `references/installation-and-troubleshooting.md` and stop.

Read `references/migration.md` for the requested migration, or `references/dolt.md` when Dolt participates.

In A3, return its structured unsupported result without invoking an agent. Read `references/installation-and-troubleshooting.md` only for Python/Pydantic setup failures.
