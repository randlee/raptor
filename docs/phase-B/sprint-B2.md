---
id: B.2
title: Parser reads the fields
status: planned
branch: feature/B-2-parse
worktree: ../raptor-worktrees/feature/B-2-parse
target: develop
depends_on: [B.1]
parallel_with: [B.3]
---

# Sprint B.2 — Parser reads the fields

`scripts/extract.py` reads `Created`, `Last Updated`, `Version` and the
item-level `Status`, puts them on every record, emits `TEST` and `DESIGN`
rows, and stops producing the range fields. Proven by round trip against
the B.1 templates. Line numbers refer to the file as of commit `315ddd6`.

## Exact Targets

- `scripts/extract.py`
- `tests/test_extract.py` (new); delete `tests/test_scripts.py`

## Deliverables

### Change in `extract.py`

- `extract_document_metadata` 968: read `**Version:**` and
  `**Document ID:**`; stop reading `**ID Range:**`; each field `None` when
  absent, no defaults.
- `normalize_status` 1033: return `None` for an unknown value; remove the
  default-to-Draft and its print (1051).
- `extract_requirement_id_and_title` 1107: regex
  `^##\s+([A-Z]+-[A-Z]+-\d{4}):\s*(.+)$` (was REQ/NFR/ADR only). A
  `**Document ID:** <ID>` line is the other way to declare an id.
- `process_requirement` 1183: one record per id declaration, whichever
  spelling. `type` is the id's prefix. `status` from the declaration's own
  `**Status:**` line, else the header; `created`, `last_updated`, `version`
  from the header; `document_metadata` is `{"owner": ...}`; no
  `relationships.family`; remove the print at 1194. For a Document ID
  declaration the title is the file's H1 and the body is the text after the
  header block.
- `parse_file_content` 1056: the file is a container. Which ids share a file
  does not matter; a REQ and an NFR in one file or two files parse the same.
  A file with no id declaration yields nothing (B.4 reports it).
- `main` 1563: honour `.raptor/raptor.toml` under the given root, not only
  the current directory (1645). Remove the record-model abort (1756–1765)
  and the hard-coded validation block (1766): validate every record, keep
  going, write `validation: {"issues": [], "summary": {}}`; B.4 fills it.
- `generate_json_output` 1432: keys `metadata`, `requirements`, `indexes`,
  `statistics`, `validation`. Remove `test_plans`, `test_plan_discovery`.

### Delete from `extract.py`

- The separate test-plan path, lines 192–914 (`is_test_plan` through
  `parse_test_plan`), superseded by `TEST` headings through the item rule.
- `extract_range_description` 928, `compute_family_members` 1296,
  `compute_test_plan_metrics` 1407.

### `tests/test_extract.py`

- Render `records.json` into a temp project under `docs/` with a `.raptor/`
  that ingests `docs`; run the parser; assert `requirements` equals the
  fixture's six records, order-independent, paths made relative.
- File layout is irrelevant: concatenate the rendered REQ and NFR files into
  one (second header block removed), and split nothing else; parse; assert
  all six records unchanged.
- `--project-root <tmp>` and running from inside `<tmp>` give the same
  records.

## Out of scope

Anything not named above. No diagnostics beyond an empty `validation`
block; no exit-code change; `generate_extraction_report` and the report
write stay until B.4; no change to `DOMAIN_MAP`, `PATH_DOMAIN_MAP`,
`find_cross_references`, `build_bidirectional_relationships`,
`build_indexes`, `compute_statistics`, `markdown_to_html`, `parse_subsections`.

## Ceilings

`extract.py` 1,200 lines (from 1,926); `test_extract.py` 60.

## Acceptance

- `python -m pytest -q tests/test_extract.py tests/test_record.py` passes.
- `rg -n 'test_plan|id_range|range_description|family' scripts/extract.py`
  prints nothing.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
