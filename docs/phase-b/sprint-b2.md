---
id: B.2
title: Python on the crate
status: planned
branch: feature/b-2-python-on-crate
worktree: ../raptor-worktrees/feature/b-2-python-on-crate
target: feature/b-1-schema-crate
depends_on: [B.1]
relation: must_follow B.1; imports the crate B.1 builds
---

# Sprint B.2 — Python on the crate

The three scripts are rewritten to import `raptor_schema` and own no field
name. `extract.py` becomes a file walk, a splitter and a bind loop.
`render.py` loops the field table through two templates. `load_sqlite.py`
inserts by the field table. The Phase A model, SQL and JSON Schema files are
deleted. Proven by round trip on the B.1 fixture. No crate change.

## Exact Targets

- `scripts/extract.py`, `scripts/render.py`, `scripts/load_sqlite.py`
- `templates/requirement.md.j2`, `templates/decision.md.j2` (new); delete
  `nfr.md.j2`, `design.md.j2`, `test-plan.md.j2`
- Delete `schema/record.py`, `schema/record.schema.json`, `schema/schema.sql`
- `tests/test_extract.py`, `tests/test_load.py` (new); delete
  `tests/test_scripts.py`, `tests/test_record.py`, `tests/fixtures/items.md`

## Deliverables

### `extract.py`

- `--project-root`, default the current directory. Reads
  `.raptor/raptor.toml` for `repository_id` and `.raptor/sources.toml` for
  the inventory, both under the root.
- The splitter, one function, inverting the template grammar into the label
  tree in the plan. Header block: bold lines between the H1 and the first
  `---` or `## `; trailing double spaces stripped. Record: `## <ID>: <title>`
  where the token matches `^[A-Z]+-[A-Z]{2,5}-\d{4}$`. Fields: bold lines
  before the first `###`. Sections: `###`; groups: `####` inside a section;
  labels: bold lines inside either, and text after the label on the same
  line is the label's first prose line; items: lines starting `- `, `* ` or
  `N. `, checkbox prefix kept in the text; everything else non-empty is
  prose. Lines inside a fenced code block and lines starting `|` are prose
  verbatim. Line numbers are one-based. An H2 that is not an id heading ends
  the current record; its content is file-level prose and outside the record
  model. The splitter contains no label literal.
- Per file: `raptor_schema.bind_file(tree)`. After all files:
  `check_inventory`, then `summarize`.
- Output `{"metadata": {repository, generated, files, records},` where
  `repository` is the `repository_id` of the run, metadata and not a column;
  "requirements": [...], "decisions": [...],
  "diagnostics": {"issues": [...], "summary": {...}}}`. `generated` is UTC.
  Issues ordered by file then line. Exit `1` when issues is non-empty, else
  `0`; the file is written either way. Stdout exactly one line:
  `{"index": "<path>", "files": N, "records": N, "issues": N}`. No other
  `print`.

### `render.py`

- Table from the record's id prefix; template `requirement.md.j2` for REQ
  and NFR, `decision.md.j2` for ADR. Output `<out>/<table>/<id>.md`.
- Passes `record` and `fields` (`field_table(table)`) to sc-compose. The
  template prints the H1 from the kind and title, then every `header` level
  field as `**Label:** value` with two trailing spaces, `ID Range` computed
  as `<id> through <id>`, then `---`, then `## <id>: <title>`, then every
  `item` level field. Sections come in B.3; the template has the loop
  already, over fields of level `section`, and prints nothing for them now.
- No `TEMPLATES` map, no field name in the script.

### `load_sqlite.py`

- `connection.executescript(raptor_schema.sql_ddl())`, foreign keys on.
- One insert per table with columns from `field_table`; a column whose
  shape is not scalar is stored as JSON text.
- `--dump` prints `{"requirements": [...], "decisions": [...]}` read back
  from the database, JSON columns parsed, for equality tests.

### Tests

- `test_extract.py`: render the fixture into a temp project with a
  `.raptor/` that ingests `docs`; extract; `requirements` and `decisions`
  equal the fixture, order-independent; `issues` empty; exit `0`.
  Concatenate the rendered REQ and NFR files into one file, second header
  removed: same records. `--project-root <tmp>` and running from inside
  `<tmp>` agree. One test per B.1 rule by mutating one rendered file:
  delete `**Version:**` line, `**Created:** YYYY-MM-DD`, item
  `**Status:** Whenever`, add `**Priority:** High` under a heading, add a
  `### Notes` section, copy ADR-FIX-0001 into the REQ file, a file with H1
  and header only. Each asserts the exact diagnostic object, the row effect
  and exit `1`.
- `test_load.py`: load the fixture index; `--dump` equals the index's
  records; a second load is idempotent.
- One test in `test_extract.py` asserts that no `label` from
  `field_table("requirements")` or `field_table("decisions")` occurs as a
  string anywhere in `scripts/extract.py`; the `rg` line below is the quick
  form of the same check.

## Out of scope

Anything not named above. No new rule, no parse option, no crate change,
no corpus run, no change to `.raptor/` or `docs/`.

## Ceilings

`extract.py` 200 lines; `render.py` 60; `load_sqlite.py` 50; each template
40; `test_extract.py` 90; `test_load.py` 30.

## Acceptance

- `pip install . && python -m pytest -q tests/` passes.
- `rg -n '\*\*[A-Z][A-Za-z ]+:\*\*' scripts/` prints nothing.
- `rg -n 'pydantic|record\.py|schema\.sql\b' scripts tests .github` prints
  nothing (`\b` keeps the crate's `sql_ddl` out of the match).
- `rg -c 'print\(' scripts/extract.py` prints `1`.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
