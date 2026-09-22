---
id: A.3
title: Skills to run the scripts
status: planned
branch: feature/A-3-skills
worktree: ../raptor-worktrees/feature/A-3-skills
target: develop
---

# Sprint A.3 — Skills to run the scripts

## Goal

- An agent in any of the 30-plus repositories can bring that repository's
  requirement and ADR Markdown into the database by following one skill, and
  a QA agent can query the database by following another.

## Hard Dependencies

- A.2 merged (final command-line arguments of `extract.py`).

## Exact Targets

- `skills/import-corpus/SKILL.md` (existing; update to the A.2 arguments)
- `skills/query-corpus/SKILL.md` (new)

## Deliverables

- `skills/import-corpus/SKILL.md`: run `extract.py` on the repository, read
  each diagnostic, edit that repository's Markdown until the run reports zero
  diagnostics, then run `load_sqlite.py`. Includes the five most common
  Markdown drifts and the edit that fixes each, written as invented examples.
  Ceiling 80 lines.
- `skills/query-corpus/SKILL.md`: how a QA agent opens the SQLite file and
  answers the usual questions with `sqlite3`: all requirements in a domain,
  everything that references an id, everything with a given status, the
  Markdown body of one id. One query per question. Ceiling 60 lines.

## Required Work

- Every command in both skills is run once against the consumer checkout
  before the PR opens, from outside Raptor.

## Explicit Code Samples

```sh
sqlite3 requirements.sqlite "select id, title from artifacts where domain = 'cal' and status = 'Approved';"
sqlite3 requirements.sqlite "select source_id, relation_kind from relationships where target_id = 'REQ-CORE-0001';"
```

## This Sprint Does Not Close

- Per-repository code or configuration in Raptor. There is none, by rule.

## Acceptance Criteria

- Both skill files under their ceilings; every command in them runs as written.
- No consumer names, ids, paths, or text; invented examples only.

## Required Validation

- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing
- Consumer architect agent: follow `import-corpus/SKILL.md` on the consumer
  checkout and `query-corpus/SKILL.md` on the result; report whether each step
  worked as written and any step that needed knowledge the skill did not give.
