# Phase B — The schema in Rust; the importer generic over it

Phase A left a gap: information in the Markdown files was not showing up in
rows. Closing it one field at a time cost five sprints per field, because a
field was named in seven places: model, JSON Schema, SQL, templates, parser,
loader and diagnostic rule. Phase B names a field once, in a Rust crate, and
makes everything else iterate that definition. After the first two sprints a
field costs one attribute line, its fixture values and one template line. The
remaining sprints add the REQ, NFR and ADR fields the consumer's own templates
define, and each run over the corpus reports the non-compliance it exposes,
grouped, with a remedy, for the consumer's architect to fix in the source.

Design documents and test plans are out of scope for Phase B. They return
later as their own tables on the same groups and enums.

## The model

A requirement or a decision is a record identified by `<TYPE>-<DOMAIN>-<NNNN>`.
The id is the primary key. The file is where the record lands today; which
ids share a file is not information. The range, the registry and the folder
are not information about the record either.

There are two tables, `requirements` (REQ and NFR) and `decisions` (ADR).
Columns that carry the same information in both are defined once as a
column group and reached through a trait, in the Rust sense; the crate is
where the schema lives from now on. Values the corpus fixes as a closed set
are one enum each, shared by every table.

| Column group | Columns | Tables |
|---|---|---|
| Identity | `id`, `title` | both |
| Lifecycle | `status`, `version`, `created`, `last_updated`, `owner`; B.4 adds `supersedes`, `superseded_by` | both |
| Provenance | `repository`, `path`, `line` | both |
| RelatedDocuments | `related_documents` as `{requirements, architecture_decisions, design_documents, work_items, external_references}` | both, from B.3 |

| Enum or type | Values |
|---|---|
| `Status` | Draft, Proposed, Active, Approved, Deprecated, Superseded |
| `Version` | `X.Y.Z`, each part one digit |
| `Date` | `YYYY-MM-DD` |
| `Id` | `(REQ\|NFR\|ADR)-[A-Z]{2,5}-\d{4}` |
| `RecordKind` | REQ, NFR, ADR; read from the id, selects the table |
| `Modal` | MUST, SHOULD, MUST NOT |

One column per template section. The section's schema is the set of bold
labels the consumer's template defines inside it. `Dependencies` is one
column `{requires: Id[], related: Id[]}`, not two. `Rationale` exists in
both tables under the same name with a different shape, so it is a column
in each and not a group. Labels the template does not define, such as
`Priority` and `Phase`, are reported and never stored.

Edges are not stored twice. Every id list inside a JSON column is an edge,
and a view `edges(source, path, target, position)` over the JSON columns
exposes them for queries; `path` is the edge type, for example
`dependencies.requires`. Referential integrity is an import diagnostic,
`DANGLING_REFERENCE`, not a foreign key, because a constraint cannot reach
into a JSON array and targets span two tables. `supersedes` and
`superseded_by` are scalars into the same table and are real foreign keys.

## Field attributes

Each field carries, next to its type, the four facts the importer and the
renderer need:

| Attribute | Values |
|---|---|
| `label` | the Markdown label as the template writes it, for example `Last Updated` |
| `level` | `header` (document header block, inherited by every record in the file; a record's own line wins), `item` (bold line directly under the record heading), `section` (a `###` heading whose column this is), `label` (a bold label inside a section) |
| `shape` | `text`, `date`, `version`, `status`, `id`, `id_list`, `text_list`, `statement_list`, `checklist`, `link_list`, `group`, `derived` |
| `section` | for `label` level, the section it renders under |

`derived` is a header label the template writes from the records in the
file rather than from a column. Today there is one, `ID Range`, which the
consumer's guideline requires on every multi-item file. The renderer
computes it, the binder checks each record's id lies inside it and stores
nothing. Every section column carries `text` for prose written before its
first label, so nothing an author wrote is dropped.

Outside the record model, and therefore neither stored nor reported: the
file's H1, its `## Overview` and other H2 prose that is not a record, and
the folder it sits in. Raptor renders records, not files.

The crate emits them as extension keywords in the JSON Schema; the field
table Python and the templates read is derived from that schema. Nothing is
listed twice.

## The label tree

The one Markdown-aware piece outside the templates is a splitter in Python
that inverts the template grammar into a tree. It knows no field names. Per
file:

```
{ "path": "docs/requirements.md",
  "header": { "Status": {"value": "Draft", "line": 3}, ... },
  "records": [
    { "id": "REQ-FIX-0001", "title": "…", "line": 9,
      "fields": { "Status": {"value": "Active", "line": 10} },
      "sections": [
        { "name": "Requirement Statement", "line": 12, "prose": ["…"],
          "labels": [ { "name": "MUST statements", "line": 14,
                        "prose": [], "items": [ {"text": "…", "line": 15} ] } ],
          "groups": [ { "name": "Alternative 1: X", "line": 30, "prose": [],
                        "labels": [ … ] } ] } ] } ] }
```

`bind_file` in the crate takes that tree and returns typed records and
diagnostics. Anything in the tree the schema does not claim is a diagnostic;
anything the schema requires and the tree lacks is a diagnostic.

## Diagnostics

One JSON object each: `file`, `line`, `rule`, `id`, `label`, `message`,
`allowed`, `remedy`. Every occurrence, whole inventory, one pass, grouped in
the summary by rule then label then file. Exit non-zero when any exists; the
output is still written. No autocorrection; no per-repository exception.

| Rule | Raised when | Effect on the row |
|---|---|---|
| `MISSING_ID` | a file has no `## <ID>: <title>` heading | none emitted |
| `MISSING_FIELD` | a required label is absent at its level | not emitted |
| `UNKNOWN_SECTION` | a `###` heading the table's schema does not define; `allowed` lists the sections | emitted without that section |
| `UNKNOWN_LABEL` | a bold label the section's schema does not define; `allowed` lists the labels | emitted without that label |
| `BAD_VALUE` | a shape conversion failed: date, version, status, id, checkbox | not emitted |
| `DUPLICATE_ID` | an id declared more than once in the inventory; raised at every occurrence | all emitted |
| `DANGLING_REFERENCE` | an id in any id list that no record declares | emitted |

The summary is built for surgical fixes. A thousand diagnostics are a
handful of patterns, and the summary presents them that way:

```
{ "counts": {"UNKNOWN_LABEL": 612, ...},
  "groups": [
    { "rule": "UNKNOWN_LABEL", "section": "Success Criteria", "label": "Acceptance",
      "allowed": ["Acceptance Criteria", "Test Evidence"], "count": 37,
      "files": { "calibration/requirements/req-cal-dark.md": [44, 91, 130], ... },
      "remedy": "Rename the label to one of `allowed`, or remove the line." } ] }
```

One group is one fix: one rename applied at the listed lines. The consumer's
architect works from the groups, re-runs the importer read-only, and the
groups shrink. Nothing in this repository changes in that loop.

## Keeping the code from growing under a thousand import issues

The importer has no place to put an accommodation, and the sprints are gated
so that none can be added by habit.

- **The splitter knows no labels.** It splits on `#`, `---`, `**…:**`, list
  markers and checkboxes. A label literal in Python is a defect, and the
  acceptance check `rg -n '\*\*[A-Z][A-Za-z ]+:\*\*' scripts/` printing
  nothing enforces it.
- **The binder is the schema.** The only way to make the importer accept a
  label is a field attribute in the crate, which is a schema change and is
  decided by the operator between sprints, never inside one. There is no
  regex to widen and no alias table to extend. The crate's acceptance check is that every label
  literal in `src/` occurs inside a field attribute.
- **A diagnostic is never resolved in this repository.** Sprint acceptance
  for B.3, B.4 and B.5 is that the corpus run produces the grouped report and
  exits non-zero, not that it is clean. A developer who believes a diagnostic
  is a schema defect writes that in the completion message with the group and
  does not change code.
- **Effect on rows is fixed above.** Emitting a row without an unknown label
  keeps the database usable while the corpus is being corrected, and the
  round-trip test on the fixture, which has no diagnostics, is what proves
  correctness. The corpus is never the test oracle.
- **Ceilings hold across the phase.** `extract.py` 200 lines, `render.py`
  60, `load_sqlite.py` 50, the crate's `src/` 700. A sprint that needs more
  stops and reports.

## Sprints

| Sprint | Content | Depends on |
|---|---|---|
| B.1 `raptor-schema` crate | two row types, three groups and traits, enums, field attributes for today's fields plus `created`, `last_updated`, `version`, item-level `status`; emission of SQL, JSON Schema, field table; `bind_file`, `check_inventory`; pyo3 behind a feature; maturin; CI step; fixture | — |
| B.2 Python on the crate | splitter, bind loop, render over the field table, generic load; `extract.py` from 1,926 lines to about 200; round trip proven | B.1 |
| B.3 REQ and NFR columns | `requirement_statement`, `rationale`, `success_criteria`, `dependencies`, `product_applicability`, `test_strategy`, `implementation_notes`, RelatedDocuments; `statement_list`, `checklist`, `id_list`, `link_list` shapes; edges view; corpus run | B.2 |
| B.4 ADR columns | `context`, `decision`, `rationale`, `consequences`, `alternatives`, `implementation`, `impact_analysis`, `decision_date`, `supersedes`, `superseded_by`; `group` shape; foreign keys; corpus run | B.3 |
| B.5 Own inventory; consumer run | ingest set trimmed to Raptor's two record files, which already follow the schema; importer clean over Raptor; the grouped non-compliance report | B.4 |

Every sprint is `must_follow` its predecessor; none is `parallel_safe`,
because each one edits the crate, the fixture and the tests the previous
one wrote. The five branches form one GitHub stack on `develop`
(`/gh-stack`): `feature/b-1-schema-crate` is based on `develop`, and each
later branch is based on the branch before it, as the `target` line of its
sprint document says. The worktree is created with `/sc-git-worktree
--base <target>`; the PR is created with `gh stack link <target> <branch>`
(then `gh stack link <stack#> <branch>` to grow the stack); merge-forward
after a fix to an earlier sprint is `gh stack rebase --upstack`; the stack
merges bottom-up with `gh stack merge --yes` after QA pass and green CI.
Branch, directory and file names are lower case.

One hand-written fixture, `tests/fixtures/records.json`, is the golden file
for both the Rust and the Python tests. B.1 writes it and renders it. B.2
proves the parser by round trip: render, split, bind, compare for equality.
B.3 and B.4 extend it. Diagnostics are proven by mutating rendered files one
defect at a time.

## Decisions recorded in this plan

Discussed with the operator before writing and recorded on this branch as
ADR-RAP-0004 to ADR-RAP-0006 in `docs/adr/adr-rap-product.md`, with
`docs/architecture.md` corrected to match. No sprint writes a decision.

- The schema is defined once, in Rust, in `crates/raptor-schema`. Python
  imports the crate through maturin and owns no schema.
- The id is the primary key of each table. Version is a column; Dolt commits
  are the history.
- Edges are derived from the JSON columns, not stored; integrity is a
  diagnostic; the two supersession scalars are foreign keys.
- `kind` (REQ or NFR) is stored on `requirements` rows and `repository` in
  Provenance, both derivable, both kept because "queryable by repository"
  (REQ-RAP-0004) and "all NFR" are direct queries. Strike either if unwanted.
- An `id_list` item is `{id, note}`: the link path is not stored, the
  renderer resolves it from the inventory; the trailing description after
  the link is kept as `note` so the round trip is exact.
- The requirement statement's normative lists are one `statements` list of
  `{modal, text}`, rendered under `MUST statements`, `SHOULD statements`,
  `MUST NOT statements`, the labels the corpus writes.

## Gaps closed elsewhere

| Gap | Owner |
|---|---|
| Every `UNKNOWN_LABEL`, `UNKNOWN_SECTION`, `BAD_VALUE`, `DUPLICATE_ID` and `DANGLING_REFERENCE` the corpus runs report | Consumer repository's architect, with the operator directly |
| Status values outside the enum, about a hundred lines across the corpus | same |
| Which local read model the CLI uses against a remote Dolt server | CLI phase, its own ADR |
| Test plans and design documents as tables | later phase |
| `docs/project-plan.md` row for Phase B, now stale | operator |

## Rules for every sprint

- **Unattended.** Every decision a sprint needs is in its document, this
  plan or an ADR before it starts. A sprint that reaches a choice not made
  here stops, states the choice in the completion message, and does not
  pick. No sprint writes or amends an ADR.
- **Exactly the named deliverables.** Anything else found is written in the
  completion message; it is not done.
- **The orchestrator holds the line.** The assignment is the sprint document
  verbatim, not a summary. On completion the orchestrator checks the diff
  against Exact Targets and measures every ceiling before QA sees it. A file
  outside Exact Targets, a line over a ceiling or a label literal in
  `scripts/` returns the sprint to the developer with the list, and nothing
  else is said about it. The orchestrator does not add scope, answer a
  design question inside a sprint, or accept a partial sprint.
- **Tight code.** Line ceilings are hard limits. No derive macro of our own,
  no configuration system, no plugin, no second parser.
- **Diagnostics in JSON.** As above. Readers are agents.
- **No exceptions for one repository.** The format is what the templates
  emit. A line the template would not have written is reported, not parsed.
- **One stack.** Branch from the `target` in the sprint document, never from
  `develop` directly for B.2 to B.5; PRs are linked with `gh stack link`;
  merges use `gh stack merge --yes`; rebases use `gh stack rebase --upstack`.
  Lower case for every branch, directory and file name.
- **Neutrality gate before every commit.**
  `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.

Phase B does not wait on the consumer repository's corrections.
