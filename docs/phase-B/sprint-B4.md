---
id: B.4
title: Loader, renderer and templates follow the contract
status: planned
branch: feature/B-4-load-render
worktree: ../raptor-worktrees/feature/B-4-load-render
target: develop
depends_on: [B.1]
parallel_with: [B.2, B.3]
---

# Sprint B.4 — Loader, renderer and templates follow the contract

`load_sqlite.py` and the templates consume the B.1 record shape. Built and
tested against `tests/fixtures/clean/expected-index.json` directly, so this
sprint does not wait for the extractor. `render.py` already maps all five
types and needs no change.

## Exact Targets

- `scripts/load_sqlite.py`
- `templates/requirement.md.j2`, `nfr.md.j2`, `adr.md.j2`, `design.md.j2`,
  `test-plan.md.j2`
- `tests/test_scripts.py`

## Deliverables

### `scripts/load_sqlite.py`

- `INSERT INTO artifacts` writes the twelve B.1 columns in B.1 order:
  `created`, `last_updated`, `version` come from the record's top level.
  `status` is `item["status"]`, not `.get`; a missing value is a failure.
- `records()` reads `index["requirements"]` only; drop the `artifacts`
  fallback.
- `relationship_rows` unchanged; it already skips non-list groups.
- Exit non-zero with the SQLite error on stderr if any insert fails; no
  partial database left behind.

### Templates

- Every template prints, after the title, four lines:
  `**Status:**`, `**Created:**`, `**Last Updated:**`, `**Version:**`, then
  `**Owner:** {{ record.document_metadata.owner }}`.
- Every `**ID Range:**` line and every reference to `id_range`,
  `range_description` or `family` is removed.
- Created and Last Updated print the stored value unchanged. These are
  Markdown, agent-facing, and carry no time component (REQ-RAP-0009).

### `tests/test_scripts.py`

- Fixture project copies `tests/fixtures/clean/` and its `.raptor/`.
- `load_sqlite` test: load `clean/expected-index.json` directly; assert
  `SELECT id, type, status, created, last_updated, version FROM artifacts`
  returns the six expected rows, and `relationships` holds the ADR → REQ
  reference in both directions.
- `render_each_record_type`: one record of each of the five types renders
  through its template and the output contains the four field lines and no
  `ID Range`.
- `extract_and_load_are_idempotent` and `extract_uses_repository_configuration`
  stay, pointed at the `clean/` fixture. They pass only after B.2 merges;
  mark them `xfail(strict=True)` in this sprint with the reason
  `"needs B.2"`, so that the merge of B.2 must remove the marker.

## Out of scope

Anything not named above. In particular: no change to `extract.py` or
`render.py`; no HTML rendering; no local-time formatting (there is no HTML output in Phase B);
no new templates; no schema change.

## Ceilings

- `load_sqlite.py` 60 lines; each template 30 lines; `test_scripts.py`
  120 lines.

## Acceptance

- `python -m pytest -q tests/test_scripts.py tests/test_record.py` passes,
  with the two `xfail` tests reported as expected failures.
- `sqlite3 <db> 'PRAGMA table_info(artifacts)'` lists the twelve B.1 columns.
- `rg -n 'ID Range|id_range|family|artifacts"' templates scripts/load_sqlite.py`
  prints nothing.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
