---
id: A.4
title: Convert the document templates to sc-compose
status: planned
branch: feature/A-4-templates
worktree: ../raptor-worktrees/feature/A-4-templates
target: develop
---

# Sprint A.4 — Convert the document templates to sc-compose

## Goal

- Records render back to Markdown through sc-compose templates converted from
  the consumer's existing document templates, so a document written from the
  database looks like one written by hand.

## Hard Dependencies

- A.2 merged (final record shape from the copied extractor).

## Exact Targets

- `templates/requirement.md.j2`, `templates/nfr.md.j2`, `templates/adr.md.j2`
  (existing placeholders; replace)
- `templates/design.md.j2`, `templates/test-plan.md.j2` (new)
- `scripts/render.py` (existing; switch from bare Jinja2 to sc-compose)
- `README.md` (install line for the sc-compose wheel)

## Deliverables

- Five sc-compose templates converted from the consumer's TEMPLATE-requirement,
  TEMPLATE-adr, TEMPLATE-design, and TEMPLATE-test-plan Markdown files, with
  the sc-compose frontmatter (name, version, description, required and optional
  variables, defaults) and the record fields as variables. Ceiling 60 lines each.
  Consumer wording that is boilerplate is kept; consumer names, ids, and
  examples are replaced with invented ones.
- `scripts/render.py`: renders one record or all records through sc-compose,
  choosing the template by record type. Ceiling 120 lines. Dependency:
  sc-compose (the wheel at the repository root, until it is published).

## Required Work

- Read the consumer's four TEMPLATE files and the record fields they map to.
  Where a template section has no record field, leave the section with an
  empty default rather than inventing a field.
- The test for `render.py` skips when sc-compose is not importable, so CI on
  Linux stays green until the wheel is published for Linux.

## Explicit Code Samples

```sh
pip install sc_compose-1.6.1-cp311-cp311-macosx_11_0_arm64.whl
python scripts/render.py requirements-index.json --id REQ-CORE-0001 --output-dir rendered
```

## This Sprint Does Not Close

- Byte-for-byte round trip of source documents. Rendered output follows the
  template; the source may not.
- Publishing the sc-compose wheel.

## Acceptance Criteria

- Each template under 60 lines; `render.py` under 120 lines.
- `render.py` renders all records of the existing index without error.
- Rendered output for one invented record of each type is shown in the PR body.
- Neutrality gate clean.

## Required Validation

- `python -m pytest -q tests`
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing
- Consumer architect agent: render every record of the consumer index; report
  files written, errors, and for five records per type whether the rendered
  document reads like the source document.
