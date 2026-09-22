---
id: B.2
title: Extractor parses to the contract
status: planned
branch: feature/B-2-extract-parse
worktree: ../raptor-worktrees/feature/B-2-extract-parse
target: develop
depends_on: [B.1]
parallel_with: [B.4]
---

# Sprint B.2 — Extractor parses to the contract

`scripts/extract.py` produces records that validate against the B.1
`Record` model, for every fixture under `tests/fixtures/clean/`, and
produces exactly `clean/expected-index.json`. Line numbers refer to the file
as of commit `315ddd6`.

## Exact Targets

- `scripts/extract.py`
- `tests/test_extract.py` (new)

## Deliverables

### Delete from `extract.py`

- The separate test-plan path, lines 192–914: `is_test_plan`,
  `extract_test_plans`, `parse_test_plan_id`, `extract_test_plan_id`,
  `expand_id_range`, `parse_requirement_range`,
  `extract_covered_requirements`, `parse_adr_range`, `extract_covered_adrs`,
  `extract_test_cases`, `parse_traceability_matrix_row`,
  `extract_traceability_matrix`, `parse_test_plan`.
- `extract_range_description` (line 928), `compute_family_members`
  (line 1296), `compute_test_plan_metrics` (line 1407).
- The `test_plans` and `test_plan_discovery` keys in `generate_json_output`
  (line 1432) and every call site that feeds them in `main`.

### Change in `extract.py`

- `extract_document_metadata` (line 968): read `**Version:**`; stop reading
  `**ID Range:**`; return `status`, `created`, `last_updated`, `version`,
  `owner`, each `None` when absent. No defaults, no normalisation here.
- `extract_requirement_id_and_title` (line 1107): regex accepts the `TEST`
  prefix. Pattern `^##\s+((REQ|NFR|ADR|TEST)-[A-Z]+-\d{4}):\s*(.+)$`. Any
  other `##` heading that starts with an id-like token is returned as an
  invalid heading (B.3 reports it; B.2 only surfaces it).
- `process_requirement` (line 1183): `type` from the prefix, one of
  `REQ|NFR|ADR|TEST`. Stamp `created`, `last_updated`, `version` from the
  header onto the record; `status` from the item's own `**Status:**` line
  when present, else the header. `document_metadata` is `{"owner": ...}`
  only. Remove `relationships.family`. Remove the print at line 1194.
- `parse_file_content` (line 1056): when a file has no item headings and a
  `**Document ID:**` line, emit one `DESIGN` record: id from that line,
  title from the H1, content is the whole file, `subsections` from the H2s,
  `source.section_line` is the Document ID line. When it has neither,
  emit nothing (B.3 reports it).
- `normalize_status` (line 1033): remove the default-to-Draft at line 1051;
  return `None` for a value outside the allowed set.
- `main` (line 1563): honour `.raptor/raptor.toml` under the given root, not
  only under the current directory (line 1645). Remove the record-model
  abort at lines 1756–1765; instead validate every record and keep going.
  (B.3 turns each failure into a diagnostic.)
- `generate_json_output` (line 1432): output keys `metadata`,
  `requirements`, `indexes`, `statistics`, `validation`. `validation` is
  `{"issues": [], "summary": {}}` in this sprint; B.3 fills it.

### `tests/test_extract.py`

- Run the extractor over a copy of `tests/fixtures/clean/`; assert the
  `requirements` array equals `expected-index.json["requirements"]` after
  the `source.file` paths are made relative.
- Assert every record validates against `Record`.
- Assert one record per `TEST` heading and one `DESIGN` record for
  `design.md`.
- Assert `--project-root <copy>` and running from inside the copy produce
  the same file count.
- Assert `dirty/` runs to completion (exit code not asserted here; B.3
  asserts it) and emits no record for `no-id.md`.

## Out of scope

Anything not named above. In particular: no diagnostics beyond what B.1's
model rejects; no exit-code change; no change to `generate_extraction_report`
or the text report (B.3 deletes them); no change to `DOMAIN_MAP`,
`PATH_DOMAIN_MAP`, `find_cross_references`, `build_bidirectional_relationships`,
`build_indexes`, `compute_statistics`, `markdown_to_html`.

## Ceilings

- `extract.py` 1,300 lines after the deletions (from 1,926).
- `test_extract.py` 80 lines.

## Acceptance

- `python -m pytest -q tests/test_extract.py tests/test_record.py` passes.
- Extractor over `clean/` produces `expected-index.json["requirements"]`
  exactly.
- `rg -n 'test_plan|id_range|range_description|family' scripts/extract.py`
  prints nothing.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
