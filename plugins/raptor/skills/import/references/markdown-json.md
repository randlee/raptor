# Markdown → JSON

From the target repository root, use configuration mode when it has `.raptor/`:

```sh
python3.11 /path/to/raptor/scripts/extract.py --output .build/requirements-index.json
```

For a repository without `.raptor/`, use the positional-root fallback:

```sh
python3.11 /path/to/raptor/scripts/extract.py . --output .build/requirements-index.json
```

Read each diagnostic and check the extracted-record count. Edit only the target
repository's Markdown, then rerun until diagnostics are clear and the count is
expected. Load the clean index into `.build/requirements.sqlite`:

```sh
python3.11 /path/to/raptor/scripts/load_sqlite.py .build/requirements-index.json .build/requirements.sqlite
```

Common Markdown drifts and their fixes, using invented examples:

| Drift | Extractor report and verified edit |
|---|---|
| A record heading lacks a colon. | Silently drops it (`Requirements extracted: 0`; no diagnostic). Write `## REQ-EXAMPLE-0001: Title` and verify the count recovers. |
| A heading has no identifier. | Silently drops it (`Requirements extracted: 0`; no diagnostic). Add a `REQ-`, `NFR-`, or `ADR-` identifier and verify the count recovers. |
| The document omits `**ID Range:**`. | Reports `document_metadata` and stops before writing the index. Add an ID range covering its records, then rerun successfully. |
| The owner field is absent. | Keeps the record with owner `Unknown` (count 1; no diagnostic). Add `**Owner:** Example Team` to retain the intended metadata. |
| A status is unrecognized. | Warns that it defaults to `Draft` and keeps the record (count 1). Use a recognized status such as `Approved` or `Draft`. |

Keep Markdown authoritative. The SQLite load is idempotent and replaces the
artifact and relationship rows from the index.
