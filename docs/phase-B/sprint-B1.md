---
id: B.1
title: Schema, templates, fixture
status: planned
branch: feature/B-1-schema
worktree: ../raptor-worktrees/feature/B-1-schema
target: develop
depends_on: []
---

# Sprint B.1 — Schema, templates, fixture

Add `created`, `last_updated`, `version` to the record in pydantic, JSON
schema, SQL and the templates, and write the one fixture the other sprints
round-trip.

## Exact Targets

- `schema/record.py`, `schema/record.schema.json`, `schema/schema.sql`
- `templates/requirement.md.j2`, `nfr.md.j2`, `adr.md.j2`, `design.md.j2`,
  `test-plan.md.j2` (all five become the same item grammar)
- `tests/fixtures/records.json` (new); delete `tests/fixtures/items.md`
- `tests/test_record.py`

## Deliverables

### `schema/record.py`

- `Record`: add `created: str`, `last_updated: str`, `version: str` after
  `status`; `status: str` (was `str | None`); `type: str`, the id's prefix
  (was a Literal of three; the type is whatever the id says).
- `DocumentMetadata`: `owner: str` only; remove `created`, `last_updated`,
  `id_range`, `range_description`.
- `Relationships`: remove `family`; delete class `Family`.
- Unchanged: `Source`, `Content`, `Reference`, `ReferencedBy`,
  `Subsection`, `extra="forbid"`.

### `schema/record.schema.json`

Regenerated from `Record.model_json_schema()`.

### `schema/schema.sql`

`artifacts` columns in order: `id`, `title`, `type`, `status`, `created`,
`last_updated`, `version`, `domain`, `document_metadata`, `source`,
`content`, `subsections`. The three new and `status` are `TEXT NOT NULL`.
`relationships` unchanged.

### Templates

Each template prints, after the H1, the header block

```
**Status:** {{ record.status }}  
**Created:** {{ record.created }}  
**Last Updated:** {{ record.last_updated }}  
**Version:** {{ record.version }}  
**Owner:** {{ record.document_metadata.owner }}  
```

then `---`, then `## {{ record.id }}: {{ record.title }}`, a `**Status:**`
line, and `{{ record.content.markdown }}`. All five templates, design
included, emit this same grammar; they differ only in the H1 wording. Every
`**ID Range:**` line is removed. Nothing else in the templates changes. What
these templates emit is the only format the parser accepts.

### `tests/fixtures/records.json`

`{"requirements": [...]}` (the key the scripts read today), six records in
full `Record` shape, bodies two or three plain sentences. Computed fields
(`content.html`, `content.summary`, `source.section_line`,
`subsections[].content_length`, `domain`) hold the values the parser
produces for the rendered file; this is a golden file.

| id | type | exercises |
|---|---|---|
| REQ-FIX-0001 | REQ | one H3 subsection; `referenced_by` the ADR |
| NFR-FIX-0001 | NFR | status differs from the REQ |
| ADR-FIX-0001 | ADR | body says `Satisfies REQ-FIX-0001.`; one reference |
| TEST-FIX-0001 | TEST | references REQ and NFR |
| TEST-FIX-0002 | TEST | no references |
| DESIGN-FIX-0001 | DESIGN | two H2 subsections |

Dates differ between records; owner and version are shared.

### `tests/test_record.py`

- Every fixture record validates; `record.schema.json` equals
  `Record.model_json_schema()`.
- `Record` rejects null `status`, missing `version`, and
  `document_metadata.id_range`.
- Render the fixture through `scripts/render.py` to a temp dir: six files;
  each has the five header lines and `## <id>: <title>`; no file has
  `ID Range` or `Document ID`.
- `schema.sql` executes in an in-memory SQLite without error.

## Out of scope

Anything not named above. No change to `extract.py`, `load_sqlite.py`,
`render.py`, `test_scripts.py`.

## Ceilings

`record.py` 60 lines; `schema.sql` 14; each template 25; `records.json`
200; `test_record.py` 60.

## Acceptance

- `python -m pytest -q tests/test_record.py` passes.
- `rg -n 'id_range|range_description|family|ID Range' schema templates`
  prints nothing.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
