---
id: B.3
title: Extractor validates and reports
status: planned
branch: feature/B-3-extract-validate
worktree: ../raptor-worktrees/feature/B-3-extract-validate
target: develop
depends_on: [B.2]
parallel_with: [B.4]
---

# Sprint B.3 — Extractor validates and reports

`scripts/extract.py` reports every problem in the source as one JSON object
with a fixed remedy, processes the whole inventory in one pass, exits
non-zero when any error was found, and still writes its outputs. The
readers are agents; there is no text report. Line numbers refer to the file
as of commit `315ddd6`; B.2 has already moved them, so locate by name.

## Exact Targets

- `scripts/extract.py`
- `tests/test_extract.py`

## Deliverables

### Rules

Each rule is one constant: rule name, message template, fixed remedy string.
A diagnostic is `{"file", "line", "rule", "id", "message", "remedy"}`; `id`
is `null` when no id is involved. Every occurrence is reported; nothing is
truncated; no rule stops the run.

| Rule | Raised when | Remedy |
|---|---|---|
| `MISSING_ID` | A scanned file has no item heading and no `**Document ID:**` | Add `**Document ID:** <PREFIX>-<AREA>-<NNNN>` to the header, or add `## <ID>: <title>` headings |
| `DUPLICATE_ID` | An id appears more than once in the inventory; raised at every occurrence, `message` names the other files | Give each item a unique id |
| `MISSING_HEADER_FIELD` | Any of `Status`, `Created`, `Last Updated`, `Version`, `Owner` absent from the header; one diagnostic per missing field; the file's items are not emitted | Add `**<Field>:** <value>` to the header block |
| `INVALID_DATE` | `Created` or `Last Updated` is not an ISO 8601 date (`YYYY-MM-DD`, or full ISO 8601 with a `Z` or offset) | Write the date as `YYYY-MM-DD` |
| `INVALID_STATUS` | Status value outside the set `normalize_status` already knows: Draft, Proposed, Active, Approved, Accepted, Deprecated, Superseded (case-insensitive; Accepted stored as Approved, as today) | Use one of: Draft, Proposed, Active, Approved, Deprecated, Superseded |
| `INVALID_HEADING` | A `##` heading starts with an id-like token but does not match `## <ID>: <title>` | Write the heading as `## <PREFIX>-<AREA>-<NNNN>: <title>` |
| `MODEL_REJECTED` | The `Record` model rejects a record the parser produced | Report to the Raptor repository; this is an extractor defect, not a source defect |

`INVALID_DATE` and `INVALID_STATUS` are raised for header values and for a
per-item `**Status:**` line. A file with `MISSING_HEADER_FIELD`,
`INVALID_DATE` or `INVALID_STATUS` in its header emits no items; the other
rules do not suppress items.

### Change in `extract.py`

- `normalize_status`: returning `None` raises `INVALID_STATUS`.
- `extract_document_metadata`: each `None` field raises
  `MISSING_HEADER_FIELD`; each bad date raises `INVALID_DATE`.
- `extract_requirement_id_and_title` invalid heading raises
  `INVALID_HEADING`.
- `parse_file_content`: a file with no items and no Document ID raises
  `MISSING_ID`.
- `main`: after all files are parsed, one pass over all ids raises
  `DUPLICATE_ID`; record validation failures raise `MODEL_REJECTED`. Exit
  code `1` when `validation.issues` is non-empty, `0` otherwise; the index
  JSON is written either way. Stdout: exactly one line,
  `{"index": "<path>", "files": N, "records": N, "issues": N}`.
- `generate_json_output`: `validation.issues` is the list ordered by file
  then line; `validation.summary` is `{rule: count}` for every rule, zero
  included; `report_file` and `generated_at` keys are removed.
- Delete `generate_extraction_report` (line 1467), the `--report` handling
  and the `reports/` directory write in `main`, and every remaining
  `print()` other than the single stdout line.

### `tests/test_extract.py`

- Run the extractor over a copy of `tests/fixtures/dirty/`; assert
  `validation.issues` equals `dirty/expected-issues.json["issues"]` after
  paths are made relative, and `validation.summary` equals its `summary`.
- Assert exit code `1` for `dirty/`, `0` for `clean/`.
- Assert the index file exists after the `dirty/` run and contains the good
  item from `bad-heading.md` and no item from `missing-version.md`.
- Assert stdout is one line of JSON with the four keys.
- Assert no `reports/` directory is created.

## Out of scope

Anything not named above. In particular: no new rules; no parse options; no
autocorrection of any value; no change to the record shape; no change to
`load_sqlite.py`, `render.py` or templates.

## Ceilings

- `extract.py` 1,300 lines (B.2 ceiling holds; rules replace the report).
- `test_extract.py` 140 lines (B.2's 80 plus these).

## Acceptance

- `python -m pytest -q tests/` passes.
- `dirty/` run: issues equal `expected-issues.json`, exit `1`, index written.
- `rg -n 'print\(' scripts/extract.py` shows exactly one line.
- `rg -n 'generate_extraction_report|report_file|total_errors' scripts/extract.py`
  prints nothing.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
