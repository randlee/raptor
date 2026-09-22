---
id: B.1
title: Schema and the two mechanical mappings
status: planned
branch: feature/B-1-schema
worktree: ../raptor-worktrees/feature/B-1-schema
target: develop
depends_on: []
---

# Sprint B.1 — Schema and the two mechanical mappings

The schema in `plan-phase-B.md`, written once as pydantic and once as SQL
with the same names; the sc-compose templates that map a record to
Markdown; and the one fixture every other sprint uses.

## Exact Targets

- `schema/record.py`, `schema/record.schema.json`, `schema/schema.sql`
- `scripts/render.py`
- `templates/item.md.j2` (new), `templates/design.md.j2`; delete
  `requirement.md.j2`, `nfr.md.j2`, `adr.md.j2`, `test-plan.md.j2`
- `tests/fixtures/records.json` (new); delete `tests/fixtures/items.md`
- `tests/test_record.py`

## Deliverables

### `schema/record.py`

Two models, `extra="forbid"`, no optionals:

- `Reference`: `target_id: str`, `context: str`.
- `Record`: `id: str`, `type: Literal["REQ","NFR","ADR","TEST","DESIGN"]`,
  `title: str`, `status: str`, `created: str`, `last_updated: str`,
  `version: str`, `owner: str`, `body: str`, `references: list[Reference]`.

Delete `DocumentMetadata`, `Source`, `Content`, `ReferencedBy`, `Family`,
`Relationships`, `Subsection`.

### `schema/record.schema.json`

Regenerated from `Record.model_json_schema()`.

### `schema/schema.sql`

```sql
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY, type TEXT NOT NULL, title TEXT NOT NULL,
  status TEXT NOT NULL, created TEXT NOT NULL, last_updated TEXT NOT NULL,
  version TEXT NOT NULL, owner TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS relationships (
  source_id TEXT NOT NULL REFERENCES artifacts(id),
  target_id TEXT NOT NULL, context TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS relationships_target ON relationships(target_id);
```

### Templates

`item.md.j2`, for REQ, NFR, ADR, TEST:

```
# {{ record.title }}

**Status:** {{ record.status }}  
**Created:** {{ record.created }}  
**Last Updated:** {{ record.last_updated }}  
**Version:** {{ record.version }}  
**Owner:** {{ record.owner }}  

---

## {{ record.id }}: {{ record.title }}

**Status:** {{ record.status }}  

{{ record.body }}
```

`design.md.j2`, for DESIGN: the same header block with
`**Document ID:** {{ record.id }}` as its first line, then `---`, then
`{{ record.body }}`. No item heading.

### `scripts/render.py`

- Reads `index["records"]`.
- `TEMPLATES`: `DESIGN` → `design.md.j2`; every other type → `item.md.j2`.
- Output path `<output_dir>/<type>/<id>.md`. Remove the domain directory and
  the stem/suffix collision logic (ids are unique; a repeat is a parser
  diagnostic, not a render case).

### `tests/fixtures/records.json`

`{"records": [...]}`, six records in schema shape, bodies two or three
plain sentences:

| id | type | exercises |
|---|---|---|
| REQ-FIX-0001 | REQ | body contains an H3 heading |
| NFR-FIX-0001 | NFR | different status from the REQ |
| ADR-FIX-0001 | ADR | body says `Satisfies REQ-FIX-0001.`; `references` has that one entry with that sentence as context |
| TEST-FIX-0001 | TEST | body mentions `REQ-FIX-0001` and `NFR-FIX-0001`; two references |
| TEST-FIX-0002 | TEST | no references, empty list |
| DESIGN-FIX-0001 | DESIGN | body has two H2 sections |

All six share `owner`, `version`; dates differ between records.

### `tests/test_record.py`

- Every record in `records.json` validates against `Record`.
- `record.schema.json` equals `Record.model_json_schema()`.
- `Record` rejects: a null `status`, a missing `version`, an extra key
  `domain`.
- Render `records.json` to a temp dir: six files exist at
  `<type>/<id>.md`; each contains the five header lines; item files contain
  `## <id>: <title>`; the design file contains `**Document ID:**`.
- `sqlite3` executes `schema.sql` in memory without error.

## Out of scope

Anything not named above. No change to `extract.py`, `load_sqlite.py`,
`test_scripts.py` (B.2 and B.3 replace those tests).

## Ceilings

`record.py` 30 lines; `schema.sql` 12; each template 20; `render.py` 50;
`records.json` 80; `test_record.py` 60.

## Acceptance

- `python -m pytest -q tests/test_record.py` passes.
- `rg -n 'domain|document_metadata|subsections|html|id_range|family' schema scripts/render.py templates`
  prints nothing.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
