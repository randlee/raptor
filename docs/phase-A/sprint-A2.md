---
id: A.2
title: Copy the extractor, run it, validate against the model
status: planned
branch: feature/A-2-extractor
worktree: ../raptor-worktrees/feature/A-2-extractor
target: develop
---

# Sprint A.2 — Copy the extractor, run it, validate against the model

## Goal

- Raptor's extractor is the original extractor, copied, with its hard-coded
  project root and domain list turned into command-line arguments, and its
  output validated against the A.1 model before it is written.

## Hard Dependencies

- A.1 merged (`schema/record.py`).

## Exact Targets

- `scripts/extract.py` (replace the 134-line rewrite with the copy)
- `scripts/load_sqlite.py` (existing; change only if the copied output needs it)
- `tests/test_scripts.py`, `tests/fixtures/` (existing; adjust to the copy)
- `docs/configuration.md` (restore from c4b0bb6 and trim to the files below)
- `.raptor/raptor.toml`, `.raptor/sources.toml`, `.raptor/routing.toml`,
  `.raptor/identity.json` (Raptor's own, as the worked example; identity.json
  restored from c4b0bb6)
- `README.md` (the three commands, plus `pip install markdown pydantic`)
- `.github/workflows/ci.yml` (the existing `corpus-scripts` job installs the
  two dependencies; no new job)

## Deliverables

- `scripts/extract.py`: the original 1,898-line extractor copied in. Changes
  allowed: project root, domain list, and output path become arguments;
  the eight lines that name the consumer are reworded; the import of the
  consumer's validation package is removed together with the code path that
  needs it; nothing else. Ceiling 2,000 lines. Dependencies: `markdown` and
  `pydantic` only.
- Validation step inside `extract.py`: every record is passed through
  `Record.model_validate` before the index is written; a failure is a
  diagnostic naming the file, the id, and the field. Ceiling 30 lines added.
- `scripts/load_sqlite.py`: unchanged unless the copied output has a field the
  two tables lack; ceiling stays 150 lines.
- `.raptor/` configuration: `extract.py` reads `.raptor/raptor.toml` in the
  target repository when present, follows it to `sources.toml` (roots, include
  and exclude globs) and `routing.toml` (artifact types per source), and uses
  those in place of the root and domain arguments. Arguments override. No
  `.raptor/` directory means arguments only. Ceiling 60 lines added to
  `extract.py`, TOML read with `tomllib`.
- `docs/configuration.md`: the definition of those four files, restored from
  c4b0bb6 and cut to what `extract.py` reads. Drop generated runtime state,
  locks, transactions, and profile versions. Ceiling 100 lines.

## Required Work

- Copy first, then edit. Do not rewrite functions. Do not remove test-plan
  discovery, HTML conversion, summaries, or relationship handling.
- Run the copy against the consumer checkout from outside Raptor and diff every
  field against the existing index. Report counts only in the PR body.

## Explicit Code Samples

```sh
python scripts/extract.py /path/to/docs --output requirements-index.json
python scripts/extract.py /path/to/docs --domains calibration camera --output out.json
```

## This Sprint Does Not Close

- Skills (A.3). Templates and rendering (A.4).
- Fixing consumer documents that produce diagnostics; that is the skill's job.

## Acceptance Criteria

- Against the consumer checkout, the copy yields the same record count as the
  existing index and zero field differences on every field, or each remaining
  difference is listed in the PR body with field name and count.
- Every record validates against `Record`; `load_sqlite.py` loads them all.
- `scripts/extract.py` under 2,000 lines; no new files outside the targets.
- Running `extract.py` on Raptor itself with no arguments uses `.raptor/` and
  produces Raptor's own index; the consumer architect agent's run uses either
  a `.raptor/` directory kept in the consumer checkout or arguments, and says
  which.
- Neutrality gate clean.

## Required Validation

- `python -m pytest -q tests`
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing
- Consumer architect agent: run `extract.py` on every Markdown document in the
  consumer checkout, then `load_sqlite.py`; report files, records, diagnostics
  verbatim, and row counts.
