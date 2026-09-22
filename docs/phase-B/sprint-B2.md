---
id: B.2
title: Parser, Markdown to JSON
status: planned
branch: feature/B-2-parse
worktree: ../raptor-worktrees/feature/B-2-parse
target: develop
depends_on: [B.1]
parallel_with: [B.3]
---

# Sprint B.2 — Parser, Markdown to JSON

`scripts/extract.py` becomes the inverse of the B.1 templates: it reads the
one document format and emits `Record` objects. Proven by round trip:
render `records.json`, parse the result, compare for equality. Line numbers
refer to the file as of commit `315ddd6`.

## Exact Targets

- `scripts/extract.py`
- `tests/test_extract.py` (new); delete `tests/test_scripts.py`

## Deliverables

### Delete from `extract.py`

- `DOMAIN_MAP`, `PATH_DOMAIN_MAP` and the domain lookup.
- Test-plan path, lines 192–914 (thirteen functions from `is_test_plan` to
  `parse_test_plan`).
- `extract_range_description` 928, `parse_subsections` 1119,
  `markdown_to_html` 1173, `build_bidirectional_relationships` 1272,
  `compute_family_members` 1296, `build_indexes` 1318,
  `compute_statistics` 1357, `compute_test_plan_metrics` 1407,
  `generate_extraction_report` 1467, `test_cross_platform_paths` 1859.
- Every `print()`. The record-model abort at 1756–1765 and the hard-coded
  validation block at 1766.

### Keep and change

- `extract_document_metadata` 968: read `Status`, `Created`,
  `Last Updated`, `Version`, `Owner`, `Document ID`; each `None` when
  absent; no defaults.
- `normalize_status` 1033: return `None` for an unknown value; no
  default-to-Draft (line 1051).
- `extract_requirement_id_and_title` 1107: regex
  `^##\s+((REQ|NFR|ADR|TEST)-[A-Z]+-\d{4}):\s*(.+)$`.
- `find_cross_references` 1143: returns `Reference` entries, `context` the
  sentence containing the id; excludes the item's own id.
- `process_requirement` 1183: emits a `Record`: `type` from the prefix;
  `status` from the item's `**Status:**` line, else header; `created`,
  `last_updated`, `version`, `owner` from the header; `body` the text after
  the heading (and after the item Status line) up to the next `##`,
  stripped of trailing blank lines.
- `parse_file_content` 1056: a file with item headings yields one record
  per heading. A file with no item headings and a `**Document ID:**` yields
  one `DESIGN` record: `id` from that line, `title` from the H1, `body` the
  text after the header block's `---`. A file with neither yields nothing
  (B.4 reports it).
- `main` 1563: honour `.raptor/raptor.toml` under the given root, not only
  the current directory (line 1645). Validate every record with `Record`.
  Write `{"records": [...], "validation": {"issues": [], "summary": {}}}`;
  B.4 fills `validation`. Records in file order, then heading order.

### `tests/test_extract.py`

- Render `records.json` into a temp project under `docs/` with a `.raptor/`
  that ingests `docs`; run the extractor; assert the output `records`
  equal the fixture's six records, order-independent.
- Multi-item file: concatenate the two rendered TEST files into one (second
  file's header block removed); parse; assert both records unchanged.
- Assert `--project-root <tmp>` and running from inside `<tmp>` give the
  same records.

## Out of scope

Anything not named above. No diagnostics beyond an empty `validation`
block; no exit-code change; no change to `render.py`, `load_sqlite.py`,
templates or schema.

## Ceilings

`extract.py` 350 lines (from 1,926); `test_extract.py` 60.

## Acceptance

- `python -m pytest -q tests/test_extract.py tests/test_record.py` passes.
- `rg -n 'html|domain|test_plan|id_range|family|subsection|print\(' scripts/extract.py`
  prints nothing.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
