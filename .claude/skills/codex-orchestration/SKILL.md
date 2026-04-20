---
name: codex-orchestration
version: 2.1.0
description: Orchestrate multi-sprint phases where crap (Codex) is the sole developer, with pipelined QA via quality-mgr teammate. Team-lead chooses the review type; quality-mgr chooses the reviewers.
---

# Codex Orchestration

This skill defines how team-lead orchestrates phases where **`crap` (Codex)** is the sole developer, executing sprints sequentially while QA runs in parallel via a dedicated **quality-mgr** teammate.

## Core Rule

`quality-mgr` owns QA coordination for all three review modes:

- `plan_gate`
- `sprint_review`
- `phase_ending_review`

Team-lead chooses the review type.
`quality-mgr` chooses and launches the reviewers according to `.claude/agents/quality-mgr.md`.
`quality-mgr` must re-read that prompt for every assignment.

Do not hardcode reviewer selection in team-lead messages when using this skill.

## Plan Is The Spec

For development assignments, the active plan is authoritative.

Team-lead must:

- read the active plan first
- identify the exact sprint or fix slice being assigned
- extract that sprint scope as written
- wrap it in `dev-template.xml.j2`
- send it to `crap`

Team-lead must **not**:

- reinterpret sprint scope
- rewrite deliverables into a narrower or broader task
- adjudicate design intent inside the assignment
- replace the plan with a team-lead summary

The correct workflow is:

1. read the plan
2. extract the sprint slice
3. send that slice to `crap` through the dev template

The plan is the spec.

## Task Sequencing

Team-lead must keep `crap`'s ATM inbox preloaded during phased work.

Required execution model:

- `crap` replies immediately when a task is read
- queued tasks get a receipt message, not an `atm ack`
- `atm ack` happens only when that task becomes active and execution starts
- queued assignments execute in order received unless a task explicitly says `INTERRUPT CURRENT TASK`
- for phased work, fixes are handled from earliest sprint to latest sprint before later sprint work starts
- team-lead must queue the next known task as soon as the current task is started
- do not wait for task completion or validation before queueing the next known task
- failure to queue follow-on work can stall the phase and is a workflow failure
- `crap` prioritizes queued work using the assignment/template rules, not ad hoc nudges

## Interrupt Policy

`INTERRUPT CURRENT TASK` is rare.

Valid interrupt reasons:

- `crap` is working from incorrect instructions
- `crap` is on the wrong branch or worktree
- `crap`'s current work conflicts with another agent's work
- continuing the current task would produce invalid output because the task basis is wrong

Not valid interrupt reasons:

- normal dev/QA loop findings
- ordinary sprint fix work
- a new QA finding on another branch/worktree
- team-lead preference to reprioritize work already correctly queued

Do not interrupt for normal dev/QA loop work. Queue the fix and let `crap` reach it in order.

## Nudge Text

Nudges must be short and protocol-only.

- Do not restate deliverables, acceptance criteria, or plan content in a nudge.
- Do not expand the Jinja2 task assignment into the nudge text.
- Nudges exist to restore queue/ack/start behavior, not to resend the task.
- Long narrative nudges reduce traceability and can break inbox acknowledgement discipline.

Typical nudge:

```bash
tmux send-keys -t $ATM_TEAM:1.2 "check atm for <TASK-ID>" Enter; sleep 0.5;
tmux send-keys -t $ATM_TEAM:1.2 "" Enter
```

Urgent nudge:

```bash
tmux send-keys -t $ATM_TEAM:1.2 "check atm IMMEDIATELY for <TASK-ID>" Enter; sleep 0.5;
tmux send-keys -t $ATM_TEAM:1.2 "" Enter
```

Use the urgent nudge rarely. It is for true interrupt conditions only, not normal QA/fix traffic.

## Quality Manager Spawn

Spawn once per phase as a named teammate:

```json
{
  "subagent_type": "quality-mgr",
  "name": "quality-mgr",
  "team_name": "$ATM_TEAM",
  "model": "sonnet",
  "prompt": "You are quality-mgr for Phase {P}. You will receive plan, sprint, and phase-ending QA assignments from team-lead. Re-read .claude/agents/quality-mgr.md for every assignment. Launch every reviewer with run_in_background=true. Do not perform the review inline."
}
```

## Team-lead -> quality-mgr

Always use the Jinja2 QA template and set `review_type` explicitly:

- `plan_gate`
- `sprint_review`
- `phase_ending_review`

The template must carry:

- review type
- worktree
- PR number when applicable
- deliverables
- references / design docs
- changed scope
- touched SSOT sections
- optional known findings to re-check

Pre-flight note for team-lead QA vars files:

- `artifact_regeneration_required` now defaults to `true`
- only set it to `false` when the changed scope contains no generator source paths and no golden/generated output paths
- when setting it to `false`, document the reason inline in the vars file comment

## Review-Type Rules

### Plan Gate

Use for:

- requirements updates
- sprint plans
- phase plans
- checklist/status corrections

Expected reviewers are defined by `.claude/agents/quality-mgr.md` and, for Rust work, `.claude/assets/sc-rust/quality-mgr/quality-mgr.rust.md`.

### Sprint Review

Use for:

- sprint completion QA
- fix-pass QA
- re-run QA after findings are addressed

Expected reviewers are defined by `.claude/agents/quality-mgr.md` and, for Rust work, `.claude/assets/sc-rust/quality-mgr/quality-mgr.rust.md`.

### Phase-Ending Review

Use for:

- integration branch readiness
- whole-phase closeout review

Expected reviewers are defined by `.claude/agents/quality-mgr.md` and, for Rust work, `.claude/assets/sc-rust/quality-mgr/quality-mgr.rust.md`.

## Pre-PR Merge Check

Before opening any PR, verify the branch includes all prior sprint merges:

```bash
git log origin/integrate/phase-{P}..origin/{branch} --oneline   # commits unique to branch (expected)
git log origin/{branch}..origin/integrate/phase-{P} --oneline   # commits missing from branch (must be empty)
```

If the second command shows commits, have `crap` merge forward before opening the PR:

```bash
git fetch origin && git merge origin/integrate/phase-{P}
```

Missing merges cause pre-existing test failures that block CI and cause QA agents to file false root-cause reports.

## Workflow

1. `crap` replies immediately when a new assignment is read.
2. if the assignment is not starting yet, `crap` reports it as queued behind the current task and continues active work.
3. when a queued task becomes active, `crap` runs `atm ack` and sends a start message with task id + branch/worktree.
4. as soon as `crap` starts task `N`, team-lead queues the next known task.
5. `crap` completes the task and reports branch + SHA.
6. team-lead opens PR and starts CI monitoring.
7. team-lead creates the next dev worktree for `crap`.
8. team-lead reads the active plan, extracts the next sprint slice verbatim, and sends that sprint assignment to `crap`.
9. team-lead sends the QA assignment to `quality-mgr` using `qa-template.xml.j2` with the correct `review_type`.
10. quality-mgr launches reviewers per its own prompt and returns one consolidated report.
11. team-lead schedules fixes if needed.
12. merge only after QA pass and CI green.

## Anti-Patterns

- Do not hardcode reviewer names in team-lead workflow or templates. `quality-mgr` chooses the reviewers.
- Do not rewrite sprint scope before assigning it to `crap`.
- Do not summarize the plan when the sprint can be extracted directly.
- Do not treat team-lead interpretation as authoritative over the plan text.
- Do not assume every newly delivered assignment should start immediately.
- Do not use `atm ack` as a synonym for "message received."
- Do not interrupt an in-progress sprint on another worktree for normal dev/QA loop work.
- Do not schedule a later-sprint task ahead of an earlier-sprint fix in the same phase unless the assignment explicitly overrides queue order.
- Do not wait for a task to finish before queueing the next known task.
- Do not expand task content into a nudge.
- Do not skip the repo-defined mandatory reviewers from `quality-mgr.md`.
- Do not accept sprint or phase implementation QA without fenced JSON evidence from the launched reviewers.
- Do not omit workflow steps from task messages — embed them every time; `crap` does not remember prior instructions.
- Do not open a PR without first running the Pre-PR Merge Check.
