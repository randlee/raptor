---
id: B.3
title: REQ and NFR columns
status: planned
branch: feature/b-3-req-columns
worktree: ../raptor-worktrees/feature/b-3-req-columns
target: feature/b-2-python-on-crate
depends_on: [B.2]
relation: must_follow B.2; extends the fixture, templates and tests B.2 writes
---

# Sprint B.3 — REQ and NFR columns

The `requirements` table gains the columns the consumer's requirement
template defines, one per section, plus the shared RelatedDocuments group.
Four list shapes and the edges view arrive with them. The fixture, the
templates and the tests extend. Then the importer runs over the consumer
corpus, read-only, and the grouped report is the deliverable, not a clean
run.

## Exact Targets

- `crates/raptor-schema/src/**`, `crates/raptor-schema/tests/**`
- `templates/requirement.md.j2`, `templates/decision.md.j2`
- `tests/fixtures/records.json`, `tests/test_extract.py`, `tests/test_load.py`
- `docs/phase-b/corpus-run-b3.md` (new)

## Deliverables

### Shapes

- `text_list`: list items as strings.
- `statement_list`: items under `MUST statements`, `SHOULD statements`,
  `MUST NOT statements` collected into one list of `{modal, text}`; the
  renderer groups them back under the three labels.
- `checklist`: items as `{text, checked}`, `checked` true for `[x]`, false
  for `[ ]`, absent when the item has no box.
- `id_list`: items as `{id, note}`; the item is a bare id or a Markdown link
  whose text is an id; `note` is the text after the link, if any; the link
  path is not stored. A non-id item is `BAD_VALUE`.
- `link_list`: items as `{text, href, note}`.

Every section column carries `text` for prose written before its first
label, plus its labels.

### Columns on `requirements`

| Column | Section | Labels and shapes |
|---|---|---|
| `requirement_statement` | Requirement Statement | `statements`: statement_list |
| `rationale` | Rationale | text only |
| `success_criteria` | Success Criteria | `acceptance_criteria`: checklist; `test_evidence`: text_list |
| `dependencies` | Dependencies | `requires`: id_list; `related`: id_list |
| `product_applicability` | Product Applicability | `applies_to`: text_list; `does_not_apply_to`: text_list |
| `implementation_notes` | Implementation Notes | `key_considerations`: text_list |
| `test_strategy` | Test Strategy | `test_types`: text_list |

### RelatedDocuments group, both tables

`related_documents`, section Related Documents: `requirements`: id_list;
`architecture_decisions`: id_list; `design_documents`, `work_items`,
`external_references`: link_list. Trait `HasRelatedDocuments`; the group
reaches `decisions` in this sprint with no further work.

Every column is `NOT NULL` JSON text; an absent section is the empty
object. Required sections, per the consumer's template: Requirement
Statement, Rationale, Success Criteria. The others are optional.

### Edges and integrity

- `sql_ddl()` emits `CREATE VIEW edges (source, path, target, position)` as
  a `UNION ALL` over every `id_list` field of every table via `json_each`,
  generated from the field tables.
- `check_inventory` adds `DANGLING_REFERENCE` for every `id_list` item whose
  id no record declares, at the item's line, with the label.

### Fixture, templates, tests

- REQ-FIX-0001 and NFR-FIX-0001 gain every column above with two or three
  items each; REQ-FIX-0001 requires NFR-FIX-0001; ADR-FIX-0001 lists
  REQ-FIX-0001 under `related_documents.requirements`; one acceptance
  criterion checked, one unchecked, one without a box.
- Templates: the section loop prints `### <Section>`, `text`, then each
  label as `**Label:**` followed by its items, with the shape deciding the
  item form. Both templates share the loop verbatim.
- Rust: one test per shape; `DANGLING_REFERENCE`; the edges view returns
  the fixture's three edges.
- Python: round trip still equality; mutations for `**Acceptance:**` under
  Success Criteria (`UNKNOWN_LABEL` with `allowed` of the two labels), a
  non-id item under `Requires` (`BAD_VALUE`), an id nothing declares
  (`DANGLING_REFERENCE`); `--dump` equality; `SELECT * FROM edges` count.

### Corpus run

Run `extract.py` over the consumer repository checkout, read-only. Write
`docs/phase-b/corpus-run-b3.md`: the consumer commit, file and record
counts per table, exit code, and the summary groups as a table of rule,
section, label, count, number of files, `allowed`. No file paths and no
repository name appear in the file; the full JSON stays untracked and is
handed to the operator. The consumer repository is "the consumer
repository".

## Out of scope

Anything not named above. No ADR content columns, no `group` shape, no
foreign keys, no fix to any diagnostic by code, no change to `extract.py`,
`load_sqlite.py` or `.raptor/`.

## Ceilings

Crate `src/` 570 lines total; crate tests 350; `records.json` 260; each
template 60; `test_extract.py` 120; `test_load.py` 40;
`corpus-run-b3.md` 60.

## Acceptance

- `cargo test -p raptor-schema`, `cargo clippy --all-targets --all-features -- -D warnings`,
  `pip install . && python -m pytest -q tests/` pass.
- `rg -n '\*\*[A-Z][A-Za-z ]+:\*\*' scripts/` prints nothing.
- The corpus run exits `1` and `corpus-run-b3.md` exists with its groups.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
