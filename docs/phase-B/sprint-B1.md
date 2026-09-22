---
id: B.1
title: Schema contract and fixtures
status: planned
branch: feature/B-1-schema
worktree: ../raptor-worktrees/feature/B-1-schema
target: develop
depends_on: []
---

# Sprint B.1 — Schema contract and fixtures

Defines what every other Phase B sprint builds against: the record model, the
SQL that initialises the database, and Markdown fixtures that comply with the
model together with the exact JSON they must produce. No script changes.

## Exact Targets

- `schema/record.py`
- `schema/record.schema.json`
- `schema/schema.sql`
- `tests/test_record.py`
- `tests/fixtures/**` (new files allowed here only)

## Deliverables

### `schema/record.py`

- `Record.type`: `Literal["REQ", "NFR", "ADR", "TEST", "DESIGN"]`.
- `Record.status`: `str` (was `str | None`).
- New required fields on `Record`: `created: str`, `last_updated: str`,
  `version: str`. ISO 8601 date as written in the source (REQ-RAP-0009),
  never null.
- `DocumentMetadata`: `owner: str` only. Remove `created`, `last_updated`,
  `id_range`, `range_description`.
- `Relationships`: remove `family`. Delete class `Family`.
- Everything else unchanged: `Source`, `Content`, `Reference`,
  `ReferencedBy`, `Subsection`, `extra="forbid"`.

### `schema/record.schema.json`

- Regenerated from `Record.model_json_schema()`. The existing test asserts
  equality; it keeps passing.

### `schema/schema.sql`

- `artifacts` columns, in order: `id TEXT NOT NULL`, `title TEXT NOT NULL`,
  `type TEXT NOT NULL`, `status TEXT NOT NULL`, `created TEXT NOT NULL`,
  `last_updated TEXT NOT NULL`, `version TEXT NOT NULL`, `domain TEXT`,
  `document_metadata TEXT NOT NULL`, `source TEXT NOT NULL`,
  `content TEXT NOT NULL`, `subsections TEXT NOT NULL`.
- `relationships` table and index unchanged.

### `tests/fixtures/`

Replace `items.md` with two directories. These are the Markdown artifacts
that comply with the schema; B.2, B.3 and B.4 are tested against them.

- `clean/` — every file has the header block `**Status:**`, `**Created:**`,
  `**Last Updated:**`, `**Version:**`, `**Owner:**`:
  - `requirements.md`: one `## REQ-FIX-0001:` and one `## NFR-FIX-0001:`
    item; the NFR carries its own `**Status:**` line that differs from the
    header.
  - `adr.md`: one `## ADR-FIX-0001:` item that mentions `REQ-FIX-0001`.
  - `test-plan.md`: two `## TEST-FIX-0001:` / `## TEST-FIX-0002:` items.
  - `design.md`: `**Document ID:** DESIGN-FIX-0001`, an H1, no item headings.
  - `expected-index.json`: the exact `requirements` array (six records) and
    `validation` block (`issues: []`, `summary` all zero) the extractor must
    produce for `clean/`, in file order, ids ascending within a file.
- `dirty/` — one problem per file, plus the expected diagnostics:
  - `no-id.md`: header block, an H1, no items, no Document ID.
  - `missing-version.md`: one REQ item; header lacks `**Version:**`.
  - `bad-date.md`: one REQ item; `**Created:** YYYY-MM-DD`.
  - `bad-status.md`: one REQ item; `**Status:** Whenever`.
  - `bad-heading.md`: one good REQ item and one line `## REQ-FIX-9 no colon`.
  - `dup-a.md`, `dup-b.md`: both define `## REQ-FIX-0002:`; `dup-a.md`
    also defines it twice.
  - `expected-issues.json`: the exact `validation.issues` array (objects
    with `file`, `line`, `rule`, `id`, `message`, `remedy`) and `summary`
    for `dirty/`, ordered by file then line.
- `.raptor/` for the fixture project: `raptor.toml`, `sources.toml` (root
  `docs`), `routing.toml` (all five artifact types), so tests copy one tree.

### `tests/test_record.py`

- Keep the schema-equality assertion.
- Replace the inline fixture with the first record of
  `clean/expected-index.json`; assert every record in that file validates.
- Assert `Record` rejects a record with `status: null`, with a missing
  `version`, and with `document_metadata.id_range` present.

## Out of scope

Anything not named above. In particular: no change to any script, template
or test other than `tests/test_record.py`; no new model fields beyond the
three named; no change to `Source`, `Content`, `Subsection`.

## Ceilings

- `record.py` 70 lines; `schema.sql` 14 lines; each fixture Markdown file
  40 lines; `test_record.py` 40 lines.

## Acceptance

- `python -m pytest -q tests/test_record.py` passes.
- `schema/record.schema.json` equals `Record.model_json_schema()`.
- `sqlite3 :memory: < schema/schema.sql` succeeds.
- Every record in `clean/expected-index.json` validates against `Record`;
  every object in `dirty/expected-issues.json` has exactly the six keys.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
