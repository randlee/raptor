---
id: B.5
title: Own inventory; consumer run
status: planned
branch: feature/b-5-own-inventory
worktree: ../raptor-worktrees/feature/b-5-own-inventory
target: feature/b-4-adr-columns
depends_on: [B.4]
relation: must_follow B.4; the consumer run needs every column
---

# Sprint B.5 — Own inventory; consumer run

Raptor's ingest set is trimmed to the two files that are records, the
importer is proven clean over Raptor itself, and the final consumer run is
recorded with the grouped report that is the hand-over to the consumer's
architect. No code change and no product document change; `docs/requirements.md`
and `docs/adr/adr-rap-product.md` already follow the schema.

## Exact Targets

- `.raptor/sources.toml`, `.raptor/identity.json`
- `docs/phase-b/consumer-run.md` (new)

## Deliverables

### Own inventory

- `.raptor/sources.toml` includes only `docs/requirements.md` and
  `docs/adr/*.md`. `identity.json` keeps the two entries and drops the rest.

### Consumer run

Run `extract.py` and `load_sqlite.py` over the consumer repository checkout,
read-only. Write `docs/phase-b/consumer-run.md`: the consumer commit, files
scanned, records per table, exit code, whether `load_sqlite.py --dump`
equals the index's records, and the summary groups as a table of rule,
section, label, count, number of files, `allowed`, ordered by count. A
closing table lists each group's count in the B.3, B.4 and this run. No file
paths and no repository name; the full JSON stays untracked and goes to the
operator, who hands it to the consumer's architect.

## Out of scope

Anything not named above. No script, crate or template change; no change to
any file under `docs/` other than the new report; no fix to consumer source;
no import skill.

## Ceilings

`consumer-run.md` 80 lines; `sources.toml` diff removes lines only.

## Acceptance

- `python scripts/extract.py --project-root .` over Raptor: `issues` empty,
  exit `0`, one `requirements` row per REQ-RAP id, one `decisions` row per
  ADR-RAP id.
- `pip install . && python -m pytest -q tests/` passes.
- Consumer run: exit `1`; every emitted row has every column non-null;
  `--dump` equals the index; `consumer-run.md` exists with its tables.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
