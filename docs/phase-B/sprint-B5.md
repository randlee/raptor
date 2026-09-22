---
id: B.5
title: Raptor's own documents comply; consumer run
status: planned
branch: feature/B-5-own-docs
worktree: ../raptor-worktrees/feature/B-5-own-docs
target: develop
depends_on: [B.4]
---

# Sprint B.5 — Raptor's own documents comply; consumer run

Raptor's requirement and ADR files are made to pass Raptor's own importer
with no diagnostic, the ingest set is trimmed to the files that are records,
and the final consumer run is recorded with the grouped report that is the
hand-over to the consumer's architect. No code change.

## Exact Targets

- `docs/requirements.md`, `docs/adr/adr-rap-product.md`
- `.raptor/sources.toml`, `.raptor/identity.json`
- `docs/phase-B/consumer-run.md` (new)

## Deliverables

### Own documents

- Each of the two files gets the header block the schema requires, directly
  under its H1: `Status`, `Created`, `Last Updated`, `Version`, `Owner`, and
  for the ADR file `Decision Date`, each line ending in two spaces, then
  `---`. `Created` is the file's first commit date, `Last Updated` its last,
  from `git log`; `Version 0.1.0`; `Status Draft`; `Owner` as written in
  `docs/requirements.md` today.
- Every `## REQ-RAP-NNNN:` item body is reorganised into the sections the
  schema defines, Requirement Statement, Rationale, Success Criteria, with
  the existing sentences moved and none added or removed. Every
  `## ADR-RAP-NNNN:` item into Context, Decision, Rationale, Consequences
  likewise. Prose under `## Overview` and `## Context` file-level headings
  stays where it is; it is outside the record model.
- `.raptor/sources.toml` includes only `docs/requirements.md` and
  `docs/adr/*.md`. `identity.json` keeps the two entries and drops the rest.

### Consumer run

Run `extract.py` and `load_sqlite.py` over the consumer repository checkout,
read-only. Write `docs/phase-B/consumer-run.md`: the consumer commit, files
scanned, records per table, exit code, whether `load_sqlite.py --dump`
equals the index's records, and the summary groups as a table of rule,
section, label, count, number of files, `allowed`, ordered by count. A
closing table lists each group's count in the B.3, B.4 and this run. No file
paths and no repository name; the full JSON stays untracked and goes to the
operator, who hands it to the consumer's architect.

## Out of scope

Anything not named above. No script, crate or template change; no fix to
consumer source; no change to `docs/project-plan.md`, `docs/architecture.md`,
`docs/configuration.md` or `docs/startup-hook.md`; no import skill.

## Ceilings

Each header block 7 lines; `consumer-run.md` 80 lines; the two product
files gain no sentence.

## Acceptance

- `python scripts/extract.py --project-root .` over Raptor: `issues` empty,
  exit `0`, one `requirements` row per REQ-RAP id, one `decisions` row per
  ADR-RAP id.
- `pip install . && python -m pytest -q tests/` passes.
- Consumer run: exit `1`; every emitted row has every column non-null;
  `--dump` equals the index; `consumer-run.md` exists with its tables.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
