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
- `templates/design.md.j2`, `templates/test-plan.md.j2` (new; the c4b0bb6
  versions under `plugins/raptor/templates/` are a starting point, 45 lines
  for all five)
- `scripts/render.py` (existing; switch from bare Jinja2 to sc-compose)
- `plugins/raptor/agents/json-markdown-export.md` and
  `skills/export/references/json-markdown.md` (restored in A.3; update the
  render command)
- `README.md` (add `pip install sc-compose`)
- `.github/workflows/ci.yml` (the existing `corpus-scripts` job adds `sc-compose` to its pip install; no new job)

## Deliverables

- Five sc-compose templates converted from the consumer's TEMPLATE-requirement,
  TEMPLATE-adr, TEMPLATE-design, and TEMPLATE-test-plan Markdown files, with
  the sc-compose frontmatter (name, version, description, required and optional
  variables, defaults) and the record fields as variables. Ceiling 60 lines each.
  Consumer wording that is boilerplate is kept; consumer names, ids, and
  examples are replaced with invented ones.
- `scripts/render.py`: renders one record or all records through sc-compose,
  choosing the template by record type. Ceiling 120 lines. Dependency:
  `sc-compose` from PyPI (1.6.1 or later), used either through its Python
  bindings or by calling the `sc-compose` CLI with `subprocess`, whichever is
  shorter.

## Required Work

- Read the consumer's four TEMPLATE files and the record fields they map to.
  Where a template section has no record field, leave the section with an
  empty default rather than inventing a field.
- The test for `render.py` renders one invented record of each type through
  sc-compose and runs in CI.

## Explicit Code Samples

```sh
pip install sc-compose
python scripts/render.py requirements-index.json --id REQ-CORE-0001 --output-dir rendered
```

## This Sprint Does Not Close

- Byte-for-byte round trip of source documents. Rendered output follows the
  template; the source may not.

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
