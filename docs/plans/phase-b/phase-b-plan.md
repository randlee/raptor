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
are not information about the record either. Nor is a repository, product
or module: a record can apply to every repository, and the link from a
consuming repository to the records it uses is a future edge declared in
that repository's `.raptor/` folder, not a column here: code points to
requirements, requirements do not point to code. File and line stay
on diagnostics, where they are used, and nowhere else.

There are two tables, `requirements` (REQ and NFR) and `decisions` (ADR).
Columns that carry the same information in both are defined once as a
column group and reached through a trait, in the Rust sense; the crate is
where the schema lives from now on. Values the corpus fixes as a closed set
are one enum each, shared by every table.

| Column group | Columns | Tables |
|---|---|---|
| Identity | `id`, `title` | both |
| Lifecycle | `status`, `version`, `created`, `last_updated`, `owner`; B.4 adds `supersedes`, `superseded_by` | both |
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

The schema stores one six-attribute entry per field. Derived export values are
not independent policy.

| Attribute | Meaning |
|---|---|
| `name` | JSON/SQL field name |
| `label` | canonical Markdown label |
| `table` | requirement, decision, or both |
| `level` | header, item, section, or label carrying its closed section enum |
| `shape` | closed value shape, carrying the modal for statement lists |
| `presence` | required, optional canonical empty value, or nullable |

`field_table(table)` exports name, label, table, level, section, shape, modal,
required, SQL type, nullable and role from those attributes. JSON Schema and
SQL DDL derive from the same definition. Only the two supersession fields
are nullable; optional section columns use their canonical empty value.
`ID Range` is derived file metadata emitted by the renderer and never stored.

Each structured section's `text` preserves prose before its first label.
A scalar section stores its text directly. The file H1, non-record H2 prose
and source folder are outside the record model. Raptor renders records,
not whole source files.

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

The Python qualifier consumes this tree and reads the crate's field table and
JSON Schema. It normalizes labels, sections, enum text and modal words by
trimming, collapsing whitespace, removing a trailing colon and casefolding,
then applies declared aliases and emits canonical JSON. It tokenizes Markdown
links and list syntax; the Rust crate contains no Markdown parser.

The crate's `accept` entry takes qualified JSON and returns an accepted batch,
structured errors and an inventory summary. A rejected record is excluded
without discarding other valid records. `Batch` is sealed, scalar constructors
validate ids, versions and dates, and enums require exact canonical spellings.
The Python boundary exposes five operations: `sql_ddl`, `json_schema`,
`field_table`, `validate_scalar`, and `accept`. Inventory checking and summary
construction remain crate-internal.

## Diagnostics

One JSON object each: `file`, `line`, `column`, `rule`, `id`, `label`,
`value`, `message`, `allowed`, `remedy`. `column` is 1-based and `value`
preserves the offending source text. Every occurrence, whole inventory, one pass, grouped in
the summary by rule then label then file. Exit non-zero when any exists; the
output is still written. No source autocorrection. Repository aliases are explicit configuration, not parser exceptions.

| Rule | Raised when | Effect on the row |
|---|---|---|
| `MISSING_ID` | a file has no `## <ID>: <title>` heading | none emitted |
| `MISSING_FIELD` | a required label is absent at its level | not emitted |
| `UNKNOWN_SECTION` | a `###` heading the table's schema does not define; `allowed` lists the sections | emitted without that section |
| `UNKNOWN_LABEL` | a bold label the section's schema does not define; `allowed` lists the labels | emitted without that label |
| `BAD_VALUE` | a shape conversion failed: date, version, status, id, checkbox | not emitted |
| `DUPLICATE_ID` | an id declared more than once in the inventory; raised at every occurrence | every duplicate occurrence rejected |
| `DANGLING_REFERENCE` | an id in any id list that no admitted record declares | emitted |

Python owns source diagnostics: missing content, unknown labels/sections and
text that cannot be qualified. Rust owns strict JSON/type/scalar errors and
inventory checks. Python maps Rust record/item positions back to source
locations. Scalar failures map to `BAD_VALUE`; duplicate and dangling-reference
categories retain their named rules. Every occurrence has its own location.
Distinct error sources may add codes; existing categories are not renamed.

Duplicate identifiers are invalid, as clarified by the user. Source inventory
checks every valid heading ID, including records rejected for other source
errors; Rust separately checks all submitted canonical-input IDs. Neither
boundary selects a first or last winner. A loader rejects duplicate rows or
carried duplicate diagnostics before opening SQLite. Replaying a unique input
updates its existing canonical rows without replacement or changing row IDs.

The summary is built for surgical fixes. A thousand diagnostics are a
handful of patterns, and the summary presents them that way:

```
{ "counts": {"UNKNOWN_LABEL": 612, ...},
  "groups": [
    { "rule": "UNKNOWN_LABEL", "section": "Success Criteria", "label": "Acceptance",
      "allowed": ["Acceptance Criteria", "Test Evidence"], "count": 37,
      "files": { "docs/requirements/req-example.md": [44, 91, 130], ... },
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
- **The schema owns canonical names.** The qualifier reads the crate's field
  metadata and JSON Schema; it has no copied field, label, section or enum
  literals. A canonical schema change requires the operator's decision.
- **Aliases belong to the consuming repository.** `.raptor/aliases.toml`
  has `labels`, `sections` and `values` tables. Targets must already be
  canonical choices; invalid targets fail configuration with file and line.
  Applications are counted in the summary. Raptor's alias tables are empty.
- **Source corrections belong to source owners.** Hand-written corpus
  diagnostics are reported, not repaired in this repository. A demonstrated
  parser defect is repaired with a regression proving the intended behavior.
- **Round-trip evidence proves content preservation.** The golden fixture and
  rendered documents must survive render, split, qualify and accept with
  equal full objects and no diagnostics. Hand-written documents are the
  diagnostic corpus. Consumer runs compare full objects against a pinned
  baseline, attribute every delta and report the actual rendered-file count.
- **Ceilings follow the governing sprint.** Later approved sprint limits
  supersede earlier estimates for the files they rebuild. B.6 specifies
  450 lines per Rust source file, 400 per Rust test file, and its named
  Python/test file ceilings. The user clarified that no whole-crate line
  limit was approved; crate totals are informational. Per-file limits remain
  hard constraints, with cohesive refactors when a limit is reached.


## Sprints

| Sprint | Content | Depends on |
|---|---|---|
| B.1 `raptor-schema` crate | two row types, three groups and traits, enums, field attributes for today's fields plus `created`, `last_updated`, `version`, item-level `status`; emission of SQL, JSON Schema, field table; `bind_file`, `check_inventory`; pyo3 behind a feature; maturin; CI step; fixture | — |
| B.2 Python on the crate | splitter, bind loop, render over the field table, generic load; `extract.py` from 1,926 lines to about 200; round trip proven | B.1 |
| B.3 REQ and NFR columns | `requirement_statement`, `rationale`, `success_criteria`, `dependencies`, `product_applicability`, `test_strategy`, `implementation_notes`, RelatedDocuments; `statement_list`, `checklist`, `id_list`, `link_list` shapes; edges view; corpus run | B.2 |
| B.4 ADR columns | `context`, `decision`, `rationale`, `consequences`, `alternatives`, `implementation`, `impact_analysis`, `decision_date`, `supersedes`, `superseded_by`; `group` shape; foreign keys; corpus run | B.3 |
| B.5 Own inventory; consumer run | ingest set trimmed to Raptor's two record files, which already follow the schema; importer clean over Raptor; the grouped non-compliance report | B.4 |
| B.6 Rebuild to specification | strict Rust ingress; Python qualification; full-object consumer comparison and phase acceptance | B.5 |

The table above records the original B.1–B.5 sequence. The separately
approved [B.6 rebuild](sprint-b-6-rebuild-to-spec.md) follows their merge into
`integrate/phase-b` and governs the strict Rust/Python qualifier boundary
described above. Its acceptance and phase-ending QA remain required; this
reconciliation does not declare the sprint complete.

Every sprint is `must_follow` its predecessor; none is `parallel_safe`.
B.2 imports the crate B.1 builds; B.3 and B.4 each extend the crate, the
fixture, the templates and the tests of the sprint before; B.5 runs the
importer with every column in place. The five branches form one GitHub stack on
`integrate/phase-b`, the phase's integration branch cut from `develop`, which
merges to `develop` when the phase ends (`/gh-stack`):
`feature/b-1-schema-crate` is based on `integrate/phase-b`, and each
later branch is based on the branch before it, as the `target` line of its
sprint document says. The worktree is created with `/sc-git-worktree
--base <target>`; the PR is created with `gh stack link <target> <branch>`
(then `gh stack link <stack#> <branch>` to grow the stack); merge-forward
after a fix to an earlier sprint is `gh stack rebase --upstack`; the stack
merges bottom-up with `gh stack merge --yes` after QA pass and green CI.
Branch, directory and file names are lower case.

One hand-written fixture, `tests/fixtures/records.json`, is the golden file
for both the Rust and the Python tests. B.1 writes it and renders it. B.2
proves the parser by round trip: render, split, qualify, accept, compare for equality.
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
- No column that is not a field in the document: no `kind` (the id prefix
  says REQ or NFR), no `repository`, `path` or `line`, no `product` or
  `module`. Operator decision, 2026-09-22, recorded in ADR-RAP-0005.
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
| Source status values outside the canonical enum after normalization or declared aliases | Consumer repository owner; canonical enum changes require operator approval |
| Which local read model the CLI uses against a remote Dolt server | CLI phase, its own ADR |
| Test plans and design documents as tables | later phase |
| Filtering by product, repository and module (REQ-RAP-0004): an edge from a consuming repository's `.raptor/` mapping to record ids, not a column | future schema version, its own ADR |

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
  emit. Consistent spelling differences require explicit repository aliases;
  unsupported source constructs are diagnosed.
- **One stack.** Branch from the `target` in the sprint document, never from
  `develop` or `integrate/phase-b` directly for B.2 to B.5; PRs are linked
  with `gh stack link --base integrate/phase-b`;
  merges use `gh stack merge --yes`; rebases use `gh stack rebase --upstack`.
  B.6 starts from `integrate/phase-b` after the original stack has merged.
  Fixes append above the pushed stack top; only the stack writer links or lands
  layers. Lower case for every branch, directory and file name.
- **Neutrality gate before every commit.**
  `rg -Pni --hidden --glob '!.git/**' --glob '!.sc/**' '(?<![[:alnum:]_])[p]3' .` prints nothing.

Phase B does not wait on the consumer repository's corrections.

## Final acceptance rulings

On 2026-10-30 the user approved ("yes/yes") the narrow generated-schema/metadata
and diagnostic JSON Value exceptions recorded in B.6, and the audited B6
before/after proof in place of missing historical per-group reports, including
the documented additional parser corrections. Strict duplicate rejection and
per-file limits remain required. Sprint status records implementation completion;
quality-mgr approved all six sprints and the whole phase in
[round 10](https://github.com/randlee/raptor/pull/85#issuecomment-6540159947). Landing remains pending.
PR #84 targets `integrate/phase-b`; the primary checkout remains on `develop`.
