---
id: A.1
title: Pydantic model of the record
status: planned
branch: feature/A-1-record-model
worktree: ../raptor-worktrees/feature/A-1-record-model
target: develop
---

# Sprint A.1 — Pydantic model of the record

## Goal

- Write the existing record schema down as one Pydantic model so every record
  the extractor produces can be validated, and so the SQL tables have a stated
  source.

## Hard Dependencies

- None. First sprint of the phase.

## Exact Targets

- `schema/record.py` (new)
- `schema/record.schema.json` (replace the hand-written 13-line file with the
  model's own JSON Schema output, committed as a file)
- `schema/schema.sql` (existing; operator review, change only if the review asks)
- `docs/architecture.md` (replace the deleted-platform text with a short
  description of the four scripts and two tables)

## Deliverables

- `schema/record.py`: one `Record` model with the ten top-level fields of the
  existing index record and nested models for `source`, `content`,
  `relationships`, and `subsections` entries, typed exactly as the existing
  index has them. Ceiling 100 lines. Pydantic v2, no other dependency.
- `schema/record.schema.json`: the output of `Record.model_json_schema()`,
  committed. No generator script; the command is written in the README.
- `schema/schema.sql`: two tables, `artifacts` and `relationships`, one column
  per top-level field, nested fields as JSON text. Ceiling 20 lines. Presented
  to the operator for review in the PR body.
- `docs/architecture.md`: ceiling 40 lines.

## Required Work

- Read the existing index and the old extractor's output section to get the
  exact field set and types. Do not add fields. Do not add provenance.
- Validate all 784 records in the existing index against the model; report the
  count that pass and every failure with field name and shape, no document text.

## Explicit Code Samples

```python
class Record(BaseModel):
    id: str
    title: str
    type: Literal["REQ", "NFR", "ADR"]
    status: str | None
    domain: str
    document_metadata: DocumentMetadata
    source: Source
    content: Content
    relationships: Relationships
    subsections: list[Subsection]
```

## This Sprint Does Not Close

- Running the model inside the extractor (A.2).
- Any change to what the extractor emits.

## Acceptance Criteria

- `schema/record.py` under 100 lines; `schema/schema.sql` under 20 lines.
- 784 of 784 records in the existing index validate; any failure is explained in
  the PR body as an index quirk, not fixed by loosening the model.
- The operator has reviewed `schema/schema.sql` in the PR.
- No new directories, packages, `pyproject`, or config files.

## Required Validation

- `python -m pytest -q tests`
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing
- Consumer architect agent: validate every record of the current index against
  the model from the consumer checkout, read-only; report pass and fail counts.
