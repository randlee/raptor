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

Restored from c4b0bb6 (`git checkout c4b0bb6 -- <path>`), then edited:

- `plugins/raptor/.claude-plugin/plugin.json`, `plugins/raptor/.codex-plugin/plugin.json`
- `plugins/raptor/skills/import/`, `plugins/raptor/skills/export/`,
  `plugins/raptor/skills/validate/` (SKILL.md and references)
- `plugins/raptor/agents/` (markdown-json-import, json-sqlite-import,
  sqlite-json-export, json-markdown-export, markdown-validate, json-validate,
  sqlite-validate, registry.yaml)

Moved and edited:

- `skills/import-corpus/SKILL.md` becomes `plugins/raptor/skills/import/references/markdown-json.md`

New:

- `plugins/raptor/skills/query/SKILL.md`

Not restored: `skills/round-trip/`, `agents/migration-round-trip.md`,
`plugin-manifest.json`, every `dolt*.md` reference, `runtime-preflight.md`,
`unsupported-responses.md`.

## Deliverables

- The restored skills and agents, each edited so every command it gives is one
  of `scripts/extract.py`, `scripts/load_sqlite.py`, `scripts/render.py`, or
  `sqlite3`, with the A.2 arguments. Mentions of the deleted runtime, Dolt,
  provenance, transactions, and profile versions are removed. Ceiling per file:
  its c4b0bb6 line count plus 20 lines.
- `import/references/markdown-json.md`: the import-corpus procedure, run
  `extract.py`, read each diagnostic, edit that repository's Markdown until the
  run reports zero diagnostics, then `load_sqlite.py`, with the five most
  common Markdown drifts and the edit that fixes each as invented examples.
  Ceiling 80 lines.
- `skills/query/SKILL.md`: how a QA agent opens the SQLite file and answers
  the usual questions with `sqlite3`: all requirements in a domain, everything
  that references an id, everything with a given status, the Markdown body of
  one id. One query per question. Ceiling 60 lines.
- Both plugin.json files point at the restored skills and agents and nothing
  else.

## Required Work

- Every command in every restored or new file is run once against the consumer
  checkout before the PR opens, from outside Raptor.

## Explicit Code Samples

```sh
sqlite3 requirements.sqlite "select id, title from artifacts where domain = 'cal' and status = 'Approved';"
sqlite3 requirements.sqlite "select source_id, relation_kind from relationships where target_id = 'REQ-CORE-0001';"
```

## This Sprint Does Not Close

- Per-repository code or configuration in Raptor. There is none, by rule.

## Acceptance Criteria

- Every file under its ceiling; every command in every file runs as written;
  no file mentions a script, module, or command that does not exist on develop.
- No consumer names, ids, paths, or text; invented examples only.

## Required Validation

- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing
- Consumer architect agent: follow the import skill on the consumer checkout
  and the query skill on the result; report whether each step
  worked as written and any step that needed knowledge the skill did not give.
