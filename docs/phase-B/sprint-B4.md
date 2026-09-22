---
id: B.4
title: ADR columns
status: planned
branch: feature/B-4-adr-columns
worktree: ../raptor-worktrees/feature/B-4-adr-columns
target: develop
depends_on: [B.3]
---

# Sprint B.4 — ADR columns

The `decisions` table gains the columns the consumer's ADR template defines,
the `group` shape for alternatives, `decision_date`, and the two supersession
scalars on Lifecycle, which reach both tables and become foreign keys. Then
the second corpus run and its report.

## Exact Targets

- `crates/raptor-schema/src/**`, `crates/raptor-schema/tests/**`
- `templates/decision.md.j2`, `templates/requirement.md.j2` (header loop only)
- `tests/fixtures/records.json`, `tests/test_extract.py`, `tests/test_load.py`
- `docs/phase-B/corpus-run-B4.md` (new)

## Deliverables

### Shape

`group`: a section whose `####` headings each start a group; the group name
is the heading text after the first `: ` (`#### Alternative 1: Name` gives
`Name`); labels inside the group are its fields. A `####` in a section not
declared as a group is `UNKNOWN_SECTION`.

### Lifecycle, both tables

`supersedes` and `superseded_by`: header level, shape `id`, optional, one
attribute line each on `Lifecycle`. SQL: nullable `TEXT REFERENCES
<same table>(id)`. An id whose kind does not match the table is `BAD_VALUE`.

### Columns on `decisions`

| Column | Section | Labels and shapes |
|---|---|---|
| `decision_date` | header `Decision Date` | date, required |
| `context` | Context | `background`: text; `problem_statement`: text |
| `decision` | Decision | `chosen_approach`: text; `key_principles`: text_list |
| `rationale` | Rationale | `benefits`: text_list; `trade_offs`: text_list |
| `consequences` | Consequences | `positive`, `negative`, `neutral`: text_list |
| `alternatives` | Alternatives Considered | group of `{name, description: text, pros: text_list, cons: text_list, why_rejected: text}` |
| `implementation` | Implementation | `key_components`, `integration_points`: text_list; `code_examples`: text |
| `impact_analysis` | Impact Analysis | `affected_components`, `performance_impact`, `security_impact`, `maintainability_impact`: text |

`rationale` on `decisions` and `rationale` on `requirements` share a name
and not a type; neither is in a group. Required sections, per the consumer's
template: Context, Decision, Rationale, Consequences. A `**Date:**` line on
an item is `UNKNOWN_LABEL` with `allowed` naming `Decision Date`.

### Fixture, templates, tests

- ADR-FIX-0001 gains every column with two alternatives; ADR-FIX-0002
  supersedes ADR-FIX-0001 and ADR-FIX-0001 is `superseded_by` 0002 with
  Status Superseded; both carry `decision_date`.
- `decision.md.j2` header loop prints `Decision Date`, `Supersedes`,
  `Superseded By` when present; the section loop prints groups as `####
  Alternative N: <name>` followed by their labels. `requirement.md.j2` gains
  the two optional header lines.
- Rust: `group` shape; foreign key accepted and rejected; kind mismatch
  `BAD_VALUE`; `Date` label diagnostic.
- Python: round trip equality; mutations for a `#### Option A` under
  Consequences (`UNKNOWN_SECTION`), `**Supersedes:** REQ-FIX-0001` on an
  ADR (`BAD_VALUE`); `--dump` equality; `PRAGMA foreign_key_check` empty.

### Corpus run

As B.3, written to `docs/phase-B/corpus-run-B4.md`, with a second table
showing each B.3 group's count then and now.

## Out of scope

Anything not named above. No test or design tables, no change to
`extract.py` or `load_sqlite.py`, no fix to any diagnostic by code, no
change to `.raptor/` or product documents.

## Ceilings

Crate `src/` 700 lines total; crate tests 420; `records.json` 360;
`decision.md.j2` 70; `test_extract.py` 140; `corpus-run-B4.md` 70.

## Acceptance

- `cargo test -p raptor-schema`, `cargo clippy --all-targets --all-features -- -D warnings`,
  `pip install . && python -m pytest -q tests/` pass.
- `rg -n '\*\*[A-Z][A-Za-z ]+:\*\*' scripts/` prints nothing.
- The corpus run exits `1` and `corpus-run-B4.md` exists with both tables.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
