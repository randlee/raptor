---
name: import
description: Route Raptor Markdown-to-JSON, JSON-to-SQLite, and future JSON-to-Dolt imports.
metadata:
  version: 1.0.0
---

# Raptor Import

## Step 1 — Verify the runtime

Run `which python3 && python3 --version` and `python3 -c 'import pydantic; print(pydantic.__version__)'`. Require Python 3.11+ and Pydantic `>=2.10,<3`. If either check fails, read `references/installation-and-troubleshooting.md` and stop.

Select only the reference matching the requested source and target:

- Markdown → JSON: read `references/markdown-json.md`.
- JSON → SQLite: read `references/json-sqlite.md`.
- JSON → Dolt: read `references/json-dolt.md`.

In A3, return the reference's fenced unsupported envelope verbatim. Do not invoke an agent or transform content.

For Python or Pydantic setup failures, read `references/installation-and-troubleshooting.md`.
