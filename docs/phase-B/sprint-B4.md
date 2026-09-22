---
id: B.4
title: Parser diagnostics
status: planned
branch: feature/B-4-diagnostics
worktree: ../raptor-worktrees/feature/B-4-diagnostics
target: develop
depends_on: [B.2]
---

# Sprint B.4 — Parser diagnostics

The parser reports every problem in the source as one JSON object with a
fixed remedy, processes the whole inventory in one pass, exits non-zero
when anything was found, and still writes its output. Readers are agents.
Defects for the tests are made by mutating rendered files, one defect each.

## Exact Targets

- `scripts/extract.py`
- `tests/test_extract.py`

## Deliverables

### Rules

A diagnostic is `{"file", "line", "rule", "id", "message", "remedy"}`;
`id` is `null` when none is involved. Each rule is one constant with its
message template and fixed remedy. Every occurrence is reported; nothing is
truncated; no rule stops the run.

| Rule | Raised when | Effect on rows | Remedy |
|---|---|---|---|
| `MISSING_ID` | file has no `## <ID>: <title>` heading | none emitted | Add a `## <PREFIX>-<AREA>-<NNNN>: <title>` heading for each record in the file |
| `DUPLICATE_ID` | an id occurs more than once in the inventory; raised at every occurrence, message names the others | all occurrences emitted | Give each item a unique id |
| `MISSING_HEADER_FIELD` | any of Status, Created, Last Updated, Version, Owner absent; one per field | file's rows not emitted | Add `**<Field>:** <value>` to the header block |
| `INVALID_DATE` | Created or Last Updated not ISO 8601 (`YYYY-MM-DD`, or full form with `Z` or offset) | file's rows not emitted | Write the date as `YYYY-MM-DD` |
| `INVALID_STATUS` | header or item Status outside Draft, Proposed, Active, Approved, Accepted, Deprecated, Superseded (case-insensitive; Accepted stored as Approved, as today) | that row not emitted | Use one of: Draft, Proposed, Active, Approved, Deprecated, Superseded |
| `INVALID_HEADING` | a `##` heading starts with an id-like token but is not `## <ID>: <title>` | that heading skipped | Write `## <PREFIX>-<AREA>-<NNNN>: <title>` |
| `MODEL_REJECTED` | `Record` rejects a parsed record | that row not emitted | Report to the Raptor repository; extractor defect |

### Change in `extract.py`

- Delete `generate_extraction_report`, the `--report` handling, the
  `reports/` write, and every remaining `print()` except the one stdout
  line below.

- Each `None` from `extract_document_metadata` raises
  `MISSING_HEADER_FIELD`; each bad date `INVALID_DATE`; `normalize_status`
  returning `None` raises `INVALID_STATUS`; the regex miss raises
  `INVALID_HEADING`; the empty file case raises `MISSING_ID`.
- `main`: after all files, one pass over ids raises `DUPLICATE_ID`; model
  failures raise `MODEL_REJECTED`. `validation.issues` ordered by file then
  line; `validation.summary` is `{rule: count}` for every rule, zeros
  included. Exit `1` when issues is non-empty, else `0`; output written
  either way. Stdout exactly one line:
  `{"index": "<path>", "files": N, "records": N, "issues": N}`.

### `tests/test_extract.py`

Starting from the rendered `records.json` project, one test per rule, each
applying one mutation and asserting the exact diagnostic object and the
exact row effect:

- delete the `**Version:**` line → `MISSING_HEADER_FIELD`, no row from that file
- `**Created:** YYYY-MM-DD` → `INVALID_DATE`
- item `**Status:** Whenever` → `INVALID_STATUS`, that row absent, others present
- heading `## REQ-FIX-9 no colon` appended → `INVALID_HEADING`, other rows intact
- copy the ADR item under the same id into the REQ file → `DUPLICATE_ID` at both lines
- a file with header block and H1 only → `MISSING_ID`
- clean project → issues empty, summary all zero, exit `0`; every mutated
  run exits `1` and still writes the index and the one stdout line.

## Out of scope

Anything not named above. No new rules; no parse options; no
autocorrection; no schema change; no change to loader, render or templates.

## Ceilings

`extract.py` 1,100 lines (below B.2's 1,200; this sprint only deletes and replaces the report); `test_extract.py` 140.

## Acceptance

- `python -m pytest -q tests/` passes.
- `rg -c 'print\(' scripts/extract.py` prints `1`.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
