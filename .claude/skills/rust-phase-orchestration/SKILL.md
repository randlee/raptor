---
name: rust-phase-orchestration
version: 1.0.0
description: Orchestrate multi-sprint phase execution as team-lead. Manages sprint waves, scrum-master lifecycle, PR merges, Codex design reviews, and integration branch strategy. This skill is for the TEAM-LEAD only, not for scrum-masters.
---

# Phase Orchestration

This skill defines how team-lead orchestrates a development phase consisting of multiple sprints with dependency-aware parallelism.

**Audience**: Team-lead only. Scrum-masters have their own process defined in `.claude/agents/scrum-master.md`.

**Substitution targets**:
- `{CODEX_AGENT}` — Codex agent used for design reviews (look up from `.atm.toml`)
- `{GITHUB_REPO}` — GitHub repo slug (e.g. `owner/repo-name`)
- `{P}` — phase number
- `{S}` — sprint number within phase
- `{slug}` — short descriptive slug for the sprint

> ⚠️ **MUST EDIT — Dev and QA Agents**
> The scrum-master spawns repo-specific dev and QA agents. Update the sprint prompt
> template below to reference the correct agent types for this repo.
> Examples:
> - agent-team-mail: `rust-developer` (dev), `rust-qa-agent` + `atm-qa-agent` (QA)
> - schook: `rust-developer` (dev), `rust-qa-agent` + `schook-qa-agent` (QA)
> Also update the agent prompt reference: `.claude/agents/scrum-master.md`

## Prerequisites

Before starting a phase:
1. Phase plan document exists with sprint specs and dependencies
2. Integration branch `integrate/phase-{P}` exists and is up to date with `develop`
3. Claude Code team (`$ATM_TEAM`) exists — do NOT recreate between phases
4. `{CODEX_AGENT}` is running and reachable via ATM CLI

## Phase Execution Loop

### 1. Build Sprint Dependency Graph

Read the phase plan and identify:
- Sprint dependencies (which sprints block others)
- Parallel waves (groups of sprints that can run concurrently)
- Merge order within each wave (to minimize conflicts on shared files)

### 2. Execute Sprints

For each sprint (respecting dependency order):

#### a. Spawn a Fresh Scrum-Master

Each sprint gets a **fresh** scrum-master — do NOT reuse scrum-masters across sprints.

```json
{
  "subagent_type": "scrum-master",
  "name": "sm-{P}-{S}",
  "team_name": "$ATM_TEAM",
  "model": "sonnet",
  "prompt": "<sprint prompt — see template below>"
}
```

**Critical rules:**
- `subagent_type` MUST be `"scrum-master"` — it has built-in dev-QA loop orchestration
- `name` parameter IS required — scrum-masters are full tmux teammates that CAN spawn background sub-agents
- `team_name` IS required — they need team membership for SendMessage
- The scrum-master is a **COORDINATOR ONLY** — it spawns dev and QA agents as background agents
- The scrum-master MUST NOT write code, run tests, or implement fixes itself
- If a scrum-master is found doing dev work, it is a bug in the orchestration

#### b. Sprint Prompt Template

> ⚠️ **MUST EDIT — Sprint Prompt**
> Update doc paths, worktree path, branch naming, and agent references for this repo.

```
You are the scrum-master for Phase {P}, Sprint {P}.{S}: {Title}.

PHASE PLAN: Read docs/{plan-file} for full context.
SPRINT SECTION: "Sprint {P}.{S}: {Title}" in the plan document.
REQUIREMENTS: Read docs/{requirements-file} for FRs and acceptance criteria.

WORKTREE:
- Create worktree via sc-git-worktree skill from integrate/phase-{P}
- Branch: feature/{P}-{S}-{slug}

PR target: integrate/phase-{P}

REMINDER: You are a COORDINATOR. Spawn dev and QA agents as background agents.
Do NOT write code, run tests, or implement fixes yourself.
Follow your standard dev-QA loop process (defined in .claude/agents/scrum-master.md).
When complete, send message to team-lead with PR number and summary.
```

#### c. Monitor Progress

- Scrum-masters report via SendMessage when done
- If a scrum-master reports subagent spawn failure, investigate and advise — do NOT tell it to do dev work itself
- If a scrum-master escalates a complex architectural question, spawn a senior reviewer agent (opus) for analysis and send findings back to scrum-master

### 3. Post-Sprint: CI Gate + Merge

After each scrum-master reports completion:

1. **Verify QA passed** — scrum-master should confirm QA agent gave PASS verdict
2. **Wait for CI** — poll PR checks until green:
   ```bash
   gh pr checks <PR> --watch
   ```
3. **Merge PR** to `integrate/phase-{P}` in dependency order
4. **Update integration branch** — pull latest into worktree
5. **Mark task completed** — TaskUpdate status to completed

### 4. Post-Sprint: Codex Design Review

**After EVERY sprint PR is merged to `integrate/phase-{P}`**, request `{CODEX_AGENT}` review:

1. Send `{CODEX_AGENT}` the diff via ATM CLI:
   ```bash
   atm send {CODEX_AGENT} "Sprint {P}.{S} merged (PR #{N}). Critical design review requested. Review: gh pr diff {N} --repo {GITHUB_REPO}. Focus: correctness bugs, architectural violations, missing edge cases."
   ```
2. Start the next eligible sprint immediately (dependency permitting) — do NOT wait for the review before continuing
3. Run the review in parallel (nudge via tmux if no reply within 2 minutes)
4. Track findings:
   - **No issues**: Continue to next sprint
   - **Issues found**: Create a **parallel fix track** in a separate worktree (`feature/{P}-fixes-arch-review`) to address findings while later sprint waves continue
5. `{CODEX_AGENT}` is authorized to implement fixes directly in the fix worktree
6. Every fix PR MUST be validated by QA agents before merge
7. Do NOT block ongoing sprint execution unless findings are marked critical/blocking

### 5. Fix Sprint (if needed)

If `{CODEX_AGENT}` found issues across sprints:
1. Create a new worktree branched from `integrate/phase-{P}` (after all sprint PRs merged)
2. `{CODEX_AGENT}` may execute fixes directly OR team-lead may delegate to a fresh scrum-master
3. Regardless of who implements fixes, run QA validation before merge
4. Follow normal CI loop and merge fix PR to integration branch
5. Request `{CODEX_AGENT}` re-review of fixes if delegated implementation was used

### 6. Wave Transitions (for parallel sprints)

Before starting the next wave:
1. All prerequisite sprints from previous wave must be merged
2. Integration branch must be updated (`git pull` in worktree)
3. Any critical/blocking findings from `{CODEX_AGENT}` must be addressed first
4. New scrum-masters get fresh worktrees branched from updated `integrate/phase-{P}`

### 7. Phase Completion

After all sprints (including fix sprint if needed) merge to `integrate/phase-{P}`:
1. Version bump (separate commit on integration branch)
2. Create PR: `integrate/phase-{P} → develop`
3. Wait for CI green
4. Merge after user approval
5. Shutdown all remaining scrum-master panes
6. Do NOT clean up worktrees until user reviews them

## Scrum-Master Lifecycle

- **Fresh per sprint** — each sprint gets a new scrum-master instance
- **Named tmux teammate** — spawned with `name` parameter for full CLI process
- **Can spawn sub-agents** — background dev and QA agents (no `name` param on sub-agents)
- **Shutdown after sprint** — send shutdown_request after PR merges and CI passes
- **NEVER does dev work** — if a scrum-master is writing code, the prompt is wrong

## Team Lifecycle

- **Team persists across phases** — NEVER use TeamDelete on persistent teams
- **Scrum-masters are ephemeral** — shutdown after their sprint completes
- **`{CODEX_AGENT}` is persistent** — communicates exclusively via ATM CLI, not SendMessage
- Between sprints: team stays alive, only scrum-master panes come and go

## ATM CLI Communication (`{CODEX_AGENT}`)

`{CODEX_AGENT}` is a Codex agent that does NOT receive Claude Code team messages. Use ATM CLI only:

```bash
atm send {CODEX_AGENT} "message"    # send
atm read                             # check replies
atm inbox                            # summary
```

Nudge via tmux if no reply within 2 minutes:
```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_title} #{pane_current_command}'
tmux send-keys -t <pane-id> -l "You have unread ATM messages. Run: atm read --team $ATM_TEAM" && sleep 0.5 && tmux send-keys -t <pane-id> Enter
```

## Task Tracking

Create one task per sprint at phase start:
- Set dependencies via `addBlockedBy`
- Assign owner when scrum-master starts
- Mark completed when PR merges

## Anti-Patterns

- Do NOT use a dev agent type as `subagent_type` for scrum-masters — use `scrum-master`
- Do NOT tell scrum-masters to "do the work yourself" — they are coordinators
- Do NOT do dev or QA work as team-lead — delegate to scrum-masters
- Do NOT skip post-merge `{CODEX_AGENT}` design review — every merged sprint requires it
- Do NOT merge fix PRs without QA validation
- Do NOT merge without QA pass + CI green
- Do NOT delete the team between sprints or phases
- Do NOT clean up worktrees without user approval
- Do NOT reuse scrum-masters across sprints — each sprint gets a fresh instance
