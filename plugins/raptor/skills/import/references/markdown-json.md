---
name: import-corpus
description: Extract a repository's Markdown artifacts into a JSON index, correct diagnostics, and load SQLite.
---

# Markdown → JSON

From the target repository, scan its Markdown into an index:

```sh
python3.11 /path/to/raptor/scripts/extract.py . --output requirements-index.json
```

Read every diagnostic, edit only the target repository's Markdown, and rerun
until the extractor reports zero validation errors. Then load the clean index:

```sh
python3.11 /path/to/raptor/scripts/load_sqlite.py requirements-index.json requirements.sqlite
```

Common Markdown drifts and their fixes, using invented examples:

| Drift | Edit |
|---|---|
| A record heading lacks a colon. | Write `## REQ-EXAMPLE-0001: Title`. |
| A heading has no identifier. | Add a `REQ-`, `NFR-`, or `ADR-` identifier. |
| The document omits `**ID Range:**`. | Add an ID range covering its records. |
| The owner field is absent. | Add `**Owner:** Example Team`. |
| A status is unrecognized. | Use a recognized status such as `Approved` or `Draft`. |

Keep Markdown authoritative. The SQLite load is idempotent and replaces the
artifact and relationship rows from the index.
