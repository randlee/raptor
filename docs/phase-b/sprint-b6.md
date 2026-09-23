---
id: B.6
title: Rebuild the crate to specification; Python qualifies
status: draft
branch: feature/b-6-rebuild-to-spec
worktree: ../raptor-worktrees/feature/b-6-rebuild-to-spec
target: integrate/phase-b
depends_on: [B.5]
relation: must_follow the merge of stack #46 into integrate/phase-b
---

# Sprint B.6 — Rebuild the crate to specification; Python qualifies

B.1 to B.5 delivered a crate that does not meet the specification. Its
`bind_file` parses Markdown fragments (links, checkbox prefixes, heading
text) that the splitter passes through verbatim, which is 599 of 1,212
lines; the 700-line ceiling was met with 40 `#[rustfmt::skip]` attributes
and lines up to 3,015 characters. The specification is: a REQ or ADR is
information; that information maps to a schema in SQL and JSON; SQL and
JSON map to each other mechanically; JSON to Markdown is mechanical through
the template; only Markdown to JSON is parsed, and that parsing is Python's
job. Everything handed to Rust is already fully qualified. Rust reads a
great deal and writes very strictly.

This sprint rebuilds the crate to that specification from the schema
outward, with the schema definition as the only code carried over, and
writes the Python qualifier against the rebuilt crate. Markdown ingress is
a one-time import per repository, so the qualifier is an import script
with exact diagnostics, not a product: its size and its tests are sized
accordingly. The rebuild is judged as new code, formatted by `cargo fmt`,
not as a diff against the old file. Evidence: RAP-B-ANALYSIS-2,
RAP-B-AUDIT-1 and RAP-B-BASELINE-1.

## Exact Targets

- `crates/raptor-schema/src/lib.rs` replaced by: `lib.rs` (pyo3 module and
  nothing else), `schema.rs` (row types, nested shapes, enums, scalar rules,
  the field table), `emit.rs` (SQL DDL, JSON Schema, field table export),
  `accept.rs` (strict ingress and the error type), `inventory.rs`
  (`check_inventory`, `summarize`)
- `crates/raptor-schema/tests/schema.rs` rewritten
- `scripts/qualify.py` (new); `scripts/extract.py`, `scripts/load_sqlite.py`
- `tests/test_qualify.py` (new); `tests/test_extract.py`, `tests/test_load.py`
- `tests/fixtures/records.json` only if a shape below requires it
- `.raptor/aliases.toml` (new, a comment and three empty tables) in Raptor
- `docs/phase-b/consumer-run-b6.md` (new)

## What is carried over, and nothing else

The schema definition is information, and it is unchanged: the `Status`,
`RecordKind` and `Modal` enums with their spellings; the `Identity` and
`Lifecycle` shapes; the nine requirement sections and nine decision
sections with their nested shapes (`Statement`, `CheckItem`, `IdItem`,
`LinkItem`, `Alternative`); the 63 field entries as information (each
entry's name, label, level, shape, section, required flag and SQL type are
kept; the entry shape they are written in is defined below and is new);
the id, version and date rules (the date rule corrected to read the full
year); the fixture.
Tests in `tests/schema.rs` that assert emitted DDL, JSON Schema or field
table content are kept where they still hold. No other line of the old
file is copied. The following do not come back in any form: `bind_file`,
the `serde_json::Value` tree helpers, `id_items`, `links`, the checklist
prefix parser, heading text handling, the case-insensitive tree lookups
(`same`, `named`, `string`, `label`, `section`), document-context
diagnostics built from tree lines, `Field::modal` by table position, the
`REQUIREMENT_SCOPE` sentinel, `#[rustfmt::skip]`.

## Deliverables

### Rust: schema and emission (`schema.rs`, `emit.rs`)

The field table is a plain `const` array of tuples, one entry per line,
each entry carrying, in this order: name, label, table (`Req`, `Dec`,
`Both`), level, shape, presence (`Required`, `Optional`, `Nullable`).
Nothing derivable is stored. The section a label belongs to is part of
its level, `Label(Related)`, where the payload is a closed `Section` enum
of fourteen variants named by the first word of the section heading
(`Statement`, `Rationale`, `Success`, `Dependencies`, `Product`,
`ImplNotes`, `Test`, `Related`, `Context`, `Decision`, `Consequences`,
`Alternatives`, `Implementation`, `Impact`); the heading text is one
exhaustive `match` on that enum. `Rationale` is one variant used by both
tables with the same heading text in each, so the match needs no table
input; the entry's table attribute says which table an entry belongs to.
The fold is safe because a label has exactly one section and a header,
item or section has none, so the type cannot express a label without a
section or a section with one. The level's payload therefore differs by
variant: `Label` carries its section, the other three carry nothing. The modal is part of the shape the same way, `Statements(MustNot)`,
with the closed `Modal` enum as payload. The SQL type is `TEXT` for every
one of today's 63 entries and is emitted from the shape. What the
qualifier needs to know about a field (heading id, heading title, header
label, section prose, section label, group) is one exhaustive `match` on
level and shape with no fallback arm; every payload is a closed enum, so
a new variant anywhere fails to compile until it is placed.

All 63 entries were written out in this encoding from the current table
and measured at the standard four-space indent: the widest is 97
characters and none exceeds 100. The two widest:

```rust
("integration_points", "Integration Points", Dec, Label(Implementation), TextList, Optional),
("architecture_decisions", "Architecture Decisions", Both, Label(Related), IdList, Optional),
```

`Nullable` is the presence of `supersedes` and `superseded_by` only;
`Optional` means the canonical empty value when the source has nothing.
`field_table(table)` exports per table the `FieldMeta` the B.1 export
already carries (name, label, level, shape, section, modal, required,
sql_type) plus `table` and `nullable`, all derived from the six stored
attributes. `json_schema()` is emitted per table with `Status`
and `Modal` choices resolvable from the schema and `x-raptor-fields`
attached per table. `validate_scalar(kind, text) -> Result<(), Error>` is
the single implementation of the id, version and date rules; Python calls
it and holds no second policy. No field is added, renamed or removed.

### Rust: strict ingress (`accept.rs`)

`accept(json) -> Result<Batch, Vec<Error>>` is the only way a record enters
the crate: `Batch` has private fields and no public constructor, so a
`Batch` value proves every record in it passed `accept`. `Id`, `Version`
and `Date` expose `as_str()` and do not implement `Deref`. Before typed
deserialization it walks the value against the
field table: unknown key anywhere, missing key, JSON type mismatch, `null`
in a non-nullable field, and an absent key where `null` is the meaning are
each an `Error`. This check exists because serde `flatten` and
`deny_unknown_fields` cannot be combined on the row types;
`deny_unknown_fields` is set on every nested type that is not flattened.
`Id`, `Version` and `Date` deserialize only through validated
constructors. Enum text is matched exactly against canonical spellings.
Supersession must name a same-kind id. A record that fails does not enter
the batch; the batch reports every failure, not the first.

One `Error` type: category, table, record position, JSON field path,
item index, offending value, cause, message. The category enum is
`UnknownKey`, `MissingKey`, `TypeMismatch`, `NullNotAllowed`,
`InvalidId`, `InvalidVersion`, `InvalidDate`, `UnknownVariant`,
`CrossKindSupersession`; variants may be added, never renamed or removed,
and Python matches on the name. It crosses pyo3 as a
structured Python exception with the same members. No `unwrap`, `expect`,
`panic!`, slice index or arithmetic on input data outside tests; every
input-dependent path returns `Result`.

### Rust: inventory (`inventory.rs`) and boundary (`lib.rs`)

`check_inventory` and `summarize` operate on an accepted batch and report
record position and item index; Python maps those to file and line. The
seven `Rule` variants are unchanged. `lib.rs` contains the pyo3 module
only: `sql_ddl`, `json_schema`, `field_table`, `validate_scalar`, `accept`,
`check_inventory`, `summarize`. Acceptance check for the whole crate:
`rg -n 'rustfmt::skip|\]\(|\*\*|- \[|serde_json::Value' crates/raptor-schema/src/`
prints nothing, `serde_json::Value` excepted inside `accept.rs`.

### SQL

Every column is `NOT NULL` except `supersedes` and `superseded_by`, which
keep their deferred same-table foreign keys. The nine section columns that
`required: false` makes nullable today become `NOT NULL` with the canonical
empty value. `CheckItem.checked` keeps its three states in JSON.
`load_sqlite.py` inserts the canonical empty value, never `NULL`, for those
columns.

### Python: the qualifier (`qualify.py`)

`qualify.py` turns the splitter's tree into qualified JSON for `accept`. It
reads `field_table` and `json_schema` at start and contains no field name,
section name, label or enum spelling of its own; the existing architecture
test is extended to it. For every label, section heading, enum value and
modal word, in this order:

1. normalise: trim, collapse internal whitespace to one space, drop a
   trailing colon, casefold;
2. apply the consuming repository's aliases (below);
3. match against the canonical choices casefolded; emit the canonical
   spelling;
4. otherwise emit a diagnostic carrying the `allowed` list. No fuzzy match,
   no edit distance, no correction the repository did not declare.

Ids, versions and dates are trimmed and passed to `validate_scalar`. Links
and id items are tokenised here (`[text](href) note`); the href of an id
item is discarded as the plan says. Missing optional content becomes the
canonical empty value of its shape; missing required content is
`MISSING_FIELD` and the record is not submitted. Every field the schema
names is present in the qualified object, `null` only in the two nullable
columns. `extract.py` keeps the splitter and the file walk and calls
`qualify` then `accept`; it grows by no more than the call sites.

### Aliases in `.raptor/`

`<repo>/.raptor/aliases.toml` declares consistent differences once:

```toml
[labels]     # bold label as written  = canonical label
"Acceptance" = "Acceptance Criteria"
[sections]   # ### heading as written = canonical section
[values]     # enum or modal text as written = canonical text
```

Keys are matched after step 1 above. An alias may only map to a canonical
choice; an alias to an unknown target is a configuration error reported
before any file is read, with the file and line of the alias. Each applied
alias is counted in the summary under `aliases`
(`{"labels": {"Acceptance -> Acceptance Criteria": 37}}`). Alias
application is not a diagnostic and does not affect the exit code. Raptor's
own file declares nothing. Whether `SHALL` → `MUST` belongs in the
consumer's file is decided by the operator from the baseline groups, not in
this sprint.

### Diagnostics at compiler grade

Every diagnostic, from the qualifier or mapped from Rust, carries `file`,
`line`, `column` (1-based, of the offending token), `rule`, `id`, `label`,
`value` (the offending text verbatim), `allowed`, `message`, `remedy`. The
message names what was found and what was expected in one sentence, so the
fix can be made from the message alone. `column` and `value` are the two
additions to the plan's diagnostic object. Inventory diagnostics report
every occurrence at its own line; id-item diagnostics report the item's
line. Both are intentional location corrections and appear in the expected
delta.

Rule ownership, which the plan's diagnostics section leaves with the
crate, is now split. The qualifier raises `MISSING_ID`, `MISSING_FIELD`
for absent source content, `UNKNOWN_SECTION`, `UNKNOWN_LABEL`, and
`BAD_VALUE` for text that does not tokenise or does not match a canonical
choice. The crate raises `BAD_VALUE` for a scalar its typed constructors
refuse, and `DUPLICATE_ID` and `DANGLING_REFERENCE` from the inventory.
Every `accept` error maps to `BAD_VALUE` with its category in `message`.

## Out of scope

Any new column or field; any ADR; any change to `templates/` or
`render.py`; any edit to a consumer document; auto-correction of source
files; an alias mechanism beyond the three tables above; fuzzy matching;
Dolt; a configuration system, plugin or derive macro of our own. A choice
this document does not make stops the sprint with the choice stated in the
completion message.

## Ceilings

Measured on `cargo fmt` output with zero `rustfmt::skip` and no line over
100 characters. Crate `src/` 1,000 lines total, no file over 450. Crate
tests 400. `extract.py` 150, `qualify.py` 250, `load_sqlite.py` 60, `render.py`
36 (unchanged). `tests/test_qualify.py` 150, `tests/test_extract.py` 150.
`consumer-run-b6.md` 100. `aliases.toml` 6. A sprint that needs more stops
and reports the number; it does not pack lines.

The estimate behind the 1,000 is reconciled against RAP-B-ANALYSIS-2 as
follows. That report's disposition table (report lines 7 to 20) keeps 463
of today's 1,212 lines; its size table (line 77) says those 463 become
1,305 lines once the skips are removed, and line 81 says the field table
alone accounts for 569 of them (8 printed lines today). So the retained
code other than the field table is 455 lines today and 736 formatted, a
growth of 1.62. Two things differ here. The field table is re-encoded as
six-element tuples with the section inside the level; every entry fits
one line (measured above), so it is 63 entries, the `Section` enum and
the declaration, about 90 lines rather than 569. And the retained set
includes `REQUIREMENT_SCOPE`, `label_for` and `table_fields` (report line
13, `lib.rs` 269 to 312, 44 lines), which this sprint deletes because the
table attribute replaces them: 44 at 1.62 is 71. Applying the report's
own ratio: 736 less 71 is 665 for retained code, plus 90 for the table,
plus the report's own strict-ingress allowance of 195 (line 78, which is
line 80's 1,500 less line 77's 1,305), gives 950.

The item-by-item estimate, counted as `cargo fmt` output: 25 types and
enums with derives at about 8 lines each, 200; field table, 90; scalar
rules, 40; emission, 120; presence walk and typed acceptance, 170;
inventory and summary, 80; pyo3 module, 60; about 760. The two methods
give 760 and 950. Both sit under 1,000; the report's method leaves only
50 lines of headroom, which is why the ceiling is not lower. The ceiling
is where the sprint stops and reports, not a target.

## Baseline and test corpus

RAP-B-BASELINE-1 pinned, at the stack head and the recorded consumer
commit: extractor SHA, toolchains, the raw index JSON, the SQLite dump, and
every diagnostic and summary group as full objects. Acceptance compares
full objects against that bundle, not counts.

Of the consumer repository's Markdown files, about four in five are
records Raptor itself rendered from the template in an earlier run. The
classification is by path: a file whose path contains a directory named
`rendered` is a rendered file; every other file is hand-written. The
consumer run reports the two counts. Those rendered files are the
qualifier's round-trip test corpus: a file the template wrote must qualify
and accept with no diagnostic, and a rule that fails on one of them is a
defect in the rule. The hand-written files are the diagnostic corpus: they
are expected to report, and a diagnostic there is never resolved in this
repository.

## Acceptance

- Round trip on the fixture: render, split, qualify, accept, compare
  equal; `issues` empty.
- `python scripts/extract.py --project-root .` over Raptor: `issues`
  empty, exit `0`, one row per REQ-RAP and ADR-RAP id.
- `cargo fmt --check`, `cargo clippy -- -D warnings`, `cargo test`,
  `pip install . && python -m pytest -q tests/` pass.
- Strict ingress tests, each proving rejection with the structured error:
  unknown key at top level and nested; missing key; wrong JSON type;
  `null` in a non-nullable field; enum text differing only by case;
  misspelled enum; malformed id, version, date; 29 February in a
  non-leap year and in years 1900 and 2000; cross-kind supersession; a
  batch with one bad record accepts the others and reports the one.
- Qualifier tests: label, section, status and modal in mixed case, with
  doubled and trailing whitespace and a trailing colon, all qualify to
  canonical spellings; a misspelling produces a diagnostic with `value`,
  `column` and `allowed`; an alias applies and is counted; an alias to an
  unknown target is refused with its line; malformed links and id items;
  statement ordering across the three labels; multi-record header carry.
- Architecture tests: no field, section, label or enum literal in
  `scripts/`; the `rg` check in the boundary section prints nothing;
  `rg -n 'unwrap\(\)|expect\(|panic!' crates/raptor-schema/src/` prints
  nothing.
- Consumer run, read-only: `consumer-run-b6.md` records, against the
  baseline, index and dump row counts (537/51 and 532/51), rule counts,
  the count of rendered files with zero diagnostics against the count of
  rendered files, and an explicit per-record and per-group delta for every
  difference, each attributed to one of: case-insensitive enum match,
  whitespace, strict required-content policy, location correction, alias,
  scalar rule change (full-year date, `validate_scalar` replacing the old
  id, version and date checks). Unexplained drift fails the sprint. No file path and no repository name.
- Every ceiling measured on formatted code and listed in the completion
  message, with the `rustfmt::skip` count, which is zero.
- Neutrality gate before every commit.

## Plan amendments this sprint needs

Applied to `docs/phase-b/plan-phase-b.md` by the operator with this
document: the label-tree section (the crate takes qualified JSON, not the
tree; the qualifier takes the tree); the "Field attributes" table (the
stored entry becomes the six attributes name, label, table, level with
the section inside it, shape with the modal inside it, presence; the
plan's four facts plus `name`, `table`, `modal`, `required`, `sql_type`
and `nullable` are what the export derives from them); the "binder is the schema" bullet (the
schema is still the only source of names; the qualifier reads it; the
sentence "no alias table to extend" goes, aliases live in the consuming
repository's `.raptor/`); the "corpus is never the test oracle" bullet
(rendered files are the round-trip corpus, hand-written files the
diagnostic corpus); the "no exceptions for one repository" bullet
(per-repository aliases are declared in that repository, not here); the
diagnostic object (`column`, `value`) and its rule ownership (the
qualifier raises the source-side rules, the crate the typed and inventory
rules, as in the diagnostics section above); the ceilings paragraph
(formatted code, zero skips, the numbers above); the "One stack" bullet
(B.6 branches from `integrate/phase-b` directly, as the first sprint after
the stack merged); the sprints table row; the "Status values outside the
enum" gap row.
