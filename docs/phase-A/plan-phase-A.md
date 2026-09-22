---
id: A
title: Import the documentation corpus into SQLite
status: planned
branch: develop
target: develop
---

# Phase A — Import the documentation corpus into SQLite

## Outcome

In the operator's words:

- This project is to formalize the schema and import the existing documentation
  repository into a SQLite database so the actual Raptor product can start, and
  so QA can query this information from the database instead of reading a
  thousand Markdown files.
- These are quick scripts plus skills to initialize a database. It is not a
  Python project. It is porting Python scripts that already existed, with a
  little clean-up.
- The Markdown files were designed to be easily parsable into JSON. The JSON
  matches the SQL. JSON to Markdown is a simple template.
- SQLite is just a quick database to develop the CLI against. It is not the
  product database.
- There are requirement and ADR documents on 30-plus repositories with
  inconsistent, hand-written Markdown. No code will handle that drift. A skill
  tells an agent how to make each repository fit the ingress pattern.

## The schema already exists

The record schema is the shape of the JSON index that the existing extractor
produces and that the consumer's web viewer renders: `id`, `title`, `type`,
`status`, `domain`, `document_metadata`, `source`, `content`, `relationships`,
`subsections`. It has been in production use since late 2025. Phase A writes it
down as a Pydantic model and two SQL tables. It does not design a new one.

## Sprint stack

| Sprint | Title | Branch | Doc |
|---|---|---|---|
| A.1 | Pydantic model of the record | `feature/A-1-record-model` | [sprint-A1.md](sprint-A1.md) |
| A.2 | Copy the extractor, run it, validate against the model | `feature/A-2-extractor` | [sprint-A2.md](sprint-A2.md) |
| A.3 | Skills to run the scripts | `feature/A-3-skills` | [sprint-A3.md](sprint-A3.md) |
| A.4 | Convert the document templates to sc-compose | `feature/A-4-templates` | [sprint-A4.md](sprint-A4.md) |

A.1 first. A.2 needs A.1 for its validation step. A.3 and A.4 follow A.2.
Each sprint is one PR to `develop` from a worktree created with
`/sc-git-worktree`.

## Rules that bound this phase

1. Only the operator adds, removes, or rewords a row in the sprint stack. An
   agent that believes a sprint is missing sends one line to the operator and
   stops. It does not edit this file or add a sprint doc.
2. Every deliverable has a line ceiling in its sprint doc. A ceiling is a hard
   limit, not a target. Exceeding it means stop and ask.
3. Every sprint's validation includes a run against the consumer documentation
   checkout, read-only, performed by the consumer architect agent, reported as
   counts and diagnostics only. Invented fixtures alone do not close a sprint.
4. No package, no runtime module, no configuration system, no plugin manifest,
   no code generation, no provenance model, no transaction log. If one seems
   needed, it is a new sprint row and only the operator can add it.
5. The plan-hardening review loop is not run on this phase. The operator's
   review of each sprint doc and each PR is the gate.
6. The string that names the consumer documentation repository never appears
   in Raptor files. CI enforces this. Consumer paths, identifiers, and document
   text stay out as well.

## What is already on develop (21c1d4c)

- `scripts/extract.py` (134 lines): a rewrite, not a copy, of the original
  extractor. Matches the existing index on all core fields for 784 records.
  Emits placeholder `content.html` and `content.summary`.
- `scripts/load_sqlite.py` (38 lines) and `schema/schema.sql` (10 lines, two
  tables). Not yet reviewed by the operator.
- `scripts/render.py` (26 lines) with three placeholder Jinja2 templates.
- `skills/import-corpus/SKILL.md` (27 lines).
- `docs/architecture.md` still describes the deleted Phase A platform and is
  corrected in A.1.

## Phase acceptance

1. The consumer architect agent runs A.2's extractor on every Markdown document
   in the consumer checkout and reports zero diagnostics, or a diagnostic per
   document that the import-corpus skill tells an agent how to fix.
2. Every record validates against the A.1 model.
3. The SQLite database holds one row per record and one row per relationship.
4. Each artifact type renders back to Markdown through an sc-compose template.
5. Total Python in `scripts/` and `schema/` stays under the sum of the sprint
   ceilings.
