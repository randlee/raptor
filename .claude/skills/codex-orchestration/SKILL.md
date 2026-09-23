---
name: codex-orchestration
version: 2.1.0
description: Orchestrate multi-sprint phases where three Codex developers execute stacked sprint work, with pipelined QA via quality-mgr teammate. Team-lead chooses the review type; quality-mgr chooses the reviewers.
---

# Codex Orchestration

This skill defines how team-lead orchestrates phases where three Codex developers — **`arap`**, **`crap`**, and **`lrap`** — execute sprint work while QA runs in parallel via a dedicated **quality-mgr** teammate.

## Core Rule

`quality-mgr` owns QA coordination for all three review modes:

- `plan_gate`
- `sprint_review`
- `phase_ending_review`

Team-lead chooses the review type.
`quality-mgr` chooses and launches the reviewers according to `.claude/agents/quality-mgr.md`.
`quality-mgr` must re-read that prompt for every assignment.
`quality-mgr` runs every assignment it holds in parallel and does not queue assignments.

Do not hardcode reviewer selection in team-lead messages when using this skill.

## Plan Is The Spec

For development assignments, the active plan is authoritative.

Team-lead must:

- read the active plan first
- identify the exact sprint or fix slice being assigned
- extract that sprint scope as written
- wrap it in `dev-template.xml.j2`
- send it to the assigned developer

Team-lead must **not**:

- reinterpret sprint scope
- rewrite deliverables into a narrower or broader task
- adjudicate design intent inside the assignment
- replace the plan with a team-lead summary

The correct workflow is:

1. read the plan
2. extract the sprint slice
3. send that slice to the assigned developer through the dev template

The plan is the spec.

## Task Sequencing

Team-lead must keep each developer's ATM inbox preloaded during phased work.

Required execution model:

- the assigned developer replies immediately when a task is read
- queued tasks get a receipt message, not an `atm ack`
- `atm ack` happens only when that task becomes active and execution starts
- queued assignments execute in order received unless a task explicitly says `INTERRUPT CURRENT TASK`
- for phased work, fixes are handled from earliest sprint to latest sprint before later sprint work starts
- team-lead must queue the next known task as soon as the current task is started
- do not wait for task completion or validation before queueing the next known task
- failure to queue follow-on work can stall the phase and is a workflow failure
- the assigned developer prioritizes queued work using the assignment/template rules, not ad hoc nudges

The team has three Codex developers: `arap`, `crap`, and `lrap`. One developer may take a fix round while another takes the next sprint. Assign medium or low difficulty fix rounds to `lrap`, and state `low`, `medium`, or `high` difficulty in every assignment.

## Interrupt Policy

`INTERRUPT CURRENT TASK` is rare.

Valid interrupt reasons:

- the assigned developer is working from incorrect instructions
- the assigned developer is on the wrong branch or worktree
- the assigned developer's current work conflicts with another agent's work
- continuing the current task would produce invalid output because the task basis is wrong

Not valid interrupt reasons:

- normal dev/QA loop findings
- ordinary sprint fix work
- a new QA finding on another branch/worktree
- team-lead preference to reprioritize work already correctly queued

Never interrupt a task in progress for fix work. Assign fix work on a new branch on top of the stack; never use the sprint branch under review.

Do not interrupt for normal dev/QA loop work. Queue the fix and let the assigned developer reach it in order.

## Nudge Text

Nudges must be short and protocol-only.

- Do not restate deliverables, acceptance criteria, or plan content in a nudge.
- Do not expand the Jinja2 task assignment into the nudge text.
- Nudges exist to restore queue/ack/start behavior, not to resend the task.
- Long narrative nudges reduce traceability and can break inbox acknowledgement discipline.

Team-lead runs on herdr. Assign development work with `atm task assign <agent> --task-id <ID> --template .claude/skills/codex-orchestration/dev-template.xml.j2 --vars <vars.json>`.
Assign QA with `.claude/skills/codex-orchestration/qa-template.xml.j2` to `quality-mgr`; QA assignments run in parallel and do not queue.

Typical nudge:

```bash
atm send <agent> "check atm for <TASK-ID>"
```

Urgent nudge:

```bash
atm send <agent> "check atm IMMEDIATELY for <TASK-ID>"
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

If the second command shows commits, have the assigned developer rebase before opening the PR:

```bash
git fetch origin && git rebase origin/integrate/phase-{P}
```

Missing merges cause pre-existing test failures that block CI and cause QA agents to file false root-cause reports.

## Stack Discipline

For stacked branches managed with `gh stack`, rebase onto the parent after every push:

```bash
git fetch origin && git rebase origin/<parent>
git push --force-with-lease origin <branch>
```

Never merge forward. Create fix branches on top of the stack and push them separately.

## Workflow

1. The assigned developer replies immediately when a new assignment is read.
2. if the assignment is not starting yet, the assigned developer reports it as queued behind the current task and continues active work.
3. when a queued task becomes active, the assigned developer runs `atm ack` and sends a start message with task id + branch/worktree.
4. as soon as a developer starts task `N`, team-lead queues the next known task.
5. the assigned developer completes the task and reports branch + SHA.
6. team-lead opens PR and starts CI monitoring.
7. team-lead creates the next dev worktree for the assigned developer.
8. team-lead reads the active plan, extracts the next sprint slice verbatim, and sends that sprint assignment to the assigned developer.
9. team-lead sends the QA assignment to `quality-mgr` using `qa-template.xml.j2` with the correct `review_type`.
10. quality-mgr launches reviewers per its own prompt and returns one consolidated report.
11. team-lead schedules fixes if needed.
12. merge only after QA pass and CI green.

## Anti-Patterns

- Do not hardcode reviewer names in team-lead workflow or templates. `quality-mgr` chooses the reviewers.
- Do not rewrite sprint scope before assigning it to a developer.
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
- Do not omit workflow steps from task messages — embed them every time; developers do not remember prior instructions.
- Do not open a PR without first running the Pre-PR Merge Check.
