---
id: B.3
title: Loader, JSON to SQL and back
status: planned
branch: feature/B-3-load
worktree: ../raptor-worktrees/feature/B-3-load
target: develop
depends_on: [B.1]
parallel_with: [B.2]
---

# Sprint B.3 — Loader, JSON to SQL and back

`scripts/load_sqlite.py` maps `Record` to the two tables with the same
field names, and back. Proven by round trip on `records.json`.

## Exact Targets

- `scripts/load_sqlite.py`
- `tests/test_load.py` (new)

## Deliverables

### `scripts/load_sqlite.py`

- Reads `index["records"]`; drop the `requirements`/`artifacts` fallbacks.
- Validates each record with `Record` before any write; a failure exits `1`
  with the pydantic message on stderr and no database change.
- `INSERT INTO artifacts` with the nine columns in schema order, taken by
  name from the record. `INSERT INTO relationships` one row per entry in
  `references`. No `json.dumps`.
- Idempotent as today: execute `schema.sql`, delete both tables, insert.
- New function `dump(database) -> {"records": [...]}` that reads both tables
  back into `Record` shape, records ordered by id, references in insertion
  order. Exposed as `--dump <database>` so the fixture can be inspected.
- Stdout one line: `{"database": "<path>", "records": N, "references": N}`.

### `tests/test_load.py`

- Load `records.json` into a temp database; `dump` equals the fixture.
- Load twice; row counts unchanged.
- `PRAGMA table_info(artifacts)` lists the nine columns in schema order.
- A record with `status: null` makes the loader exit `1` and leave no
  `artifacts` rows.

## Out of scope

Anything not named above. No change to `extract.py`, `render.py`, schema
or templates. No Dolt.

## Ceilings

`load_sqlite.py` 60 lines; `test_load.py` 50.

## Acceptance

- `python -m pytest -q tests/test_load.py tests/test_record.py` passes.
- `rg -n 'json.dumps|document_metadata|requirements' scripts/load_sqlite.py`
  prints nothing.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
