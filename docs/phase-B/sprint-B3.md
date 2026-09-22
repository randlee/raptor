---
id: B.3
title: Loader writes the columns
status: planned
branch: feature/B-3-load
worktree: ../raptor-worktrees/feature/B-3-load
target: develop
depends_on: [B.1]
parallel_with: [B.2]
---

# Sprint B.3 — Loader writes the columns

`scripts/load_sqlite.py` writes the three new columns and reads the rows
back into record shape, so the JSON to SQL mapping is proven by round trip
on `records.json`.

## Exact Targets

- `scripts/load_sqlite.py`
- `tests/test_load.py` (new)

## Deliverables

### `scripts/load_sqlite.py`

- `INSERT INTO artifacts` with the twelve B.1 columns in schema order;
  `status`, `created`, `last_updated`, `version` taken by key, not `.get`,
  so a missing value fails.
- Validate each record with `Record` before any write; a failure exits `1`
  with the pydantic message on stderr and leaves the database unchanged.
- `records()` reads `index["requirements"]` only.
- New `dump(database) -> {"requirements": [...]}`: reads both tables back
  into `Record` shape (JSON columns parsed, relationship rows regrouped into
  `references` and `referenced_by`), records ordered by id. Exposed as
  `--dump <database>`.
- Stdout one line: `{"database": "<path>", "artifacts": N, "relationships": N}`.

### `tests/test_load.py`

- Load `records.json`; `dump` equals the fixture.
- Load twice; row counts unchanged.
- `PRAGMA table_info(artifacts)` lists the twelve columns in schema order,
  `status`, `created`, `last_updated`, `version` marked NOT NULL.
- A record with `status: null` makes the loader exit `1` and leave no
  `artifacts` rows.

## Out of scope

Anything not named above. No change to `extract.py`, `render.py`, schema
or templates. No Dolt.

## Ceilings

`load_sqlite.py` 70 lines; `test_load.py` 50.

## Acceptance

- `python -m pytest -q tests/test_load.py tests/test_record.py` passes.
- `rg -n '"artifacts"|\.get\("status"\)' scripts/load_sqlite.py` prints nothing.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
