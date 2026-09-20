---
name: round-trip
description: Route Raptor semantic migration round trips while preserving canonical identity and provenance.
metadata:
  version: 1.0.0
---

# Raptor Round Trip

## Step 1 — Verify the runtime

Run `which python3 && python3 --version` and `python3 -c 'import pydantic; print(pydantic.__version__)'`. Require Python 3.11+ and Pydantic `>=2.10,<3`. If either check fails, read `references/installation-and-troubleshooting.md` and stop.

Read `references/migration.md` for the requested migration, or `references/dolt.md` when Dolt participates.

In A3, return its structured unsupported result without invoking an agent. Read `references/installation-and-troubleshooting.md` only for Python/Pydantic setup failures.
