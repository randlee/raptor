---
name: rust-phase-orchestration
version: 1.0.0
description: Orchestrate multi-sprint Rust phase execution as team-lead. Uses crap as the sole Rust developer and quality-mgr as the QA coordinator, with Rust reviewer selection delegated through quality-mgr.rust.
---

# Rust Phase Orchestration

This skill defines how team-lead runs a multi-sprint Rust phase in `raptor` without hardcoding reviewer logic into the orchestration layer.

## Audience

Team-lead only.

## Core Rule

Use the existing orchestration surfaces:
- `/codex-orchestration` for dev and QA task sequencing
- `.claude/agents/quality-mgr.md` for reviewer coordination
- `.claude/assets/sc-rust/quality-mgr/quality-mgr.rust.md` for Rust-specific reviewer selection and assignment rendering

Do not hardcode Rust reviewer names into team-lead task text beyond the installed `quality-mgr` and Rust supplement rules.

## Preconditions

Before starting a phase:

1. `docs/requirements.md` exists.
2. `docs/architecture.md` exists.
3. `docs/project-plan.md` exists and identifies sprint slices or phase work order.
4. The target base branch for the phase is known (`develop` or a dedicated integration branch).
5. `quality-mgr` is available as a named teammate and the Rust supplement is installed.

## Rust Phase Workflow

### 1. Read and Partition the Plan

Read `docs/project-plan.md` and determine:
- sprint boundaries
- dependency order
- which plan items are docs-only versus implementation work
- which items are likely to require Rust best-practices or service-hardening review

### 2. Queue Development Through `crap`

For each sprint or fix slice:

1. create or update the task entry
2. assign the sprint slice to `crap`
3. use the existing `/codex-orchestration` dev-template flow
4. preserve the active plan language instead of rewriting the sprint into a looser summary

### 3. Route QA Through `quality-mgr`

For each phase checkpoint, send QA through `quality-mgr`:

- `plan_gate` for requirements / architecture / plan updates
- `sprint_review` for completed Rust implementation work
- `phase_ending_review` for integration readiness

`quality-mgr` must re-read:
- `.claude/agents/quality-mgr.md`
- `.claude/assets/sc-rust/quality-mgr/quality-mgr.rust.md` when Rust is in scope

The Rust supplement owns:
- whether `rust-qa-agent` runs
- whether `rust-best-practices-agent` runs
- whether `rust-service-hardening-agent` runs
- how Rust assignments are rendered with `sc-compose`

### 4. PR and Merge Discipline

- open the PR as soon as dev work is ready for self-test and review
- start CI monitoring immediately
- do not merge until QA passes and CI is green
- if the work is phase-scoped, perform an explicit phase-ending review before final merge

## Rust-Specific Review Policy

- docs-only Rust planning work should use `plan_gate`
- code work should use `sprint_review`
- broader readiness or integration closeout should use `phase_ending_review`
- service-hardening review is conditional and should rely on the service-indicator logic in `quality-mgr.rust.md`

## Anti-Patterns

- do not reintroduce old reviewer names or custom Rust QA routing in team-lead messages
- do not bypass `quality-mgr` by sending ad hoc review commands directly to Rust specialist agents
- do not duplicate the Rust supplement logic in this file
- do not treat `rust-qa-agent` as the owner of architectural or pattern-review decisions

## Output

Team-lead should leave the phase in a state where:
- sprint tasks are explicitly queued
- QA mode is explicit for each checkpoint
- reviewer selection is delegated to `quality-mgr` + `quality-mgr.rust`
- merge readiness is based on evidence rather than memory
