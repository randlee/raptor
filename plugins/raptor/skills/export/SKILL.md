---
name: export
description: Route Raptor SQLite-to-JSON, JSON-to-Markdown, and future Dolt-to-JSON exports.
metadata:
  version: 1.0.0
---

# Raptor Export

## Step 1 — Verify the runtime

Run `which python3 && python3 --version` and `python3 -c 'import pydantic; print(pydantic.__version__)'`. Require Python 3.11+ and Pydantic `>=2.10,<3`. If either check fails, read `references/installation-and-troubleshooting.md` and stop.

Read only the selected reference: `references/sqlite-json.md`, `references/json-markdown.md`, or `references/dolt-json.md`.

In A3, return its structured unsupported result without invoking an agent. Read `references/installation-and-troubleshooting.md` only for Python/Pydantic setup failures.
