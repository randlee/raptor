---
id: B.5
title: Raptor's own documents comply; consumer run
status: planned
branch: feature/B-5-own-docs
worktree: ../raptor-worktrees/feature/B-5-own-docs
target: develop
depends_on: [B.2, B.3, B.4]
---

# Sprint B.5 — Raptor's own documents comply; consumer run

Raptor's `.raptor/sources.toml` ingests `docs/**/*.md`. Four of those
documents have no header block and no id, and the phase plans carry YAML
frontmatter instead of a header block. Under B.4 the parser run over
Raptor's own repository would exit non-zero. This sprint makes Raptor pass
its own gate, then runs the three scripts over the consumer corpus and
records the result. No script changes.

## Exact Targets

- `docs/architecture.md`, `docs/configuration.md`, `docs/project-plan.md`,
  `docs/startup-hook.md`
- `.raptor/sources.toml`, `.raptor/identity.json`
- `docs/phase-B/consumer-run.md` (new)

## Deliverables

### Header blocks

Each of the four documents gains, directly under its H1, the header block
`**Status:**`, `**Created:**`, `**Last Updated:**`,
`**Version:**`, `**Owner:**`, followed by `---`. Ids are the ones
`.raptor/identity.json` already assigns: `DOC-RAP-0001` requirements (already
compliant, no change), `DOC-RAP-0002` architecture, `DOC-RAP-0003` the ADR file
(already compliant, no change), `DOC-RAP-0004` project-plan. `configuration.md`
and `startup-hook.md` receive `DOC-RAP-0005` and `DOC-RAP-0006`, added to
`identity.json`. Dates come from each file's first and last commit in `git
log`; Version `0.1.0`; Status `Draft`; Owner the repository owner as written
in `docs/requirements.md`.

Each document's single record is declared the same way as any other:
`## DOC-RAP-0002: Architecture` under the header block. The ids in
`identity.json` are renumbered to four digits to match the heading rule.

### Phase plans

`docs/phase-A/**` and `docs/phase-B/**` are removed from the ingest set in
`.raptor/sources.toml` with an `exclude` entry. They are working plans with
frontmatter, not records, and adding header blocks to them adds nothing
Raptor would query.

### Consumer run

Run `extract.py`, `load_sqlite.py` and `render.py` over the consumer
repository checkout (read-only) with the merged B.2–B.4 scripts. Write
`docs/phase-B/consumer-run.md` with: commit of each repository, file count,
record count per type, `validation.summary`, exit code, the count of
`MISSING_ID` and `DUPLICATE_ID` diagnostics compared with the consumer
architect's RAP-VAL-1 report, and whether `load_sqlite.py --dump` of the
loaded database equals the parser's `records` array. The consumer repository is not named in the
file; it is "the consumer repository". Nothing in that checkout is edited.

## Out of scope

Anything not named above. In particular: no script or template change; no
fix to consumer source (that is the consumer architect's, with the operator);
no change to `docs/project-plan.md` beyond the header block (the sprint table
is operator-only); no edit to `docs/requirements.md` or the ADR file.

## Ceilings

- `consumer-run.md` 60 lines. Each header block 7 lines.

## Acceptance

- Extractor over Raptor's own repository: `validation.issues` empty, exit
  `0`, one `DOC` row per header-block document, REQ and ADR rows as
  before.
- `python -m pytest -q tests/` passes.
- Consumer run: every `artifacts` row has all nine columns non-null; one
  row per `## <ID>:` heading whatever the prefix; every id-less file and
  every repeated id appears in `validation.issues`; exit `1` until the
  source is corrected.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
