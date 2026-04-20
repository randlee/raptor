---
name: team-lead
version: 1.0.0
description: >
  Session initialization for the team-lead identity. Confirms identity and
  detects whether a full team restore is needed. Only run when
  ATM_IDENTITY=team-lead.
---

# Team Lead Skill

**Trigger**: Run at the start of every session where `ATM_IDENTITY=team-lead`.

---

## Step 0 — Confirm Identity

```bash
echo "ATM_IDENTITY=$ATM_IDENTITY"
```

Stop if `ATM_IDENTITY` is not `team-lead`.

> **TODO**: Verify no other active session is already running as `team-lead`
> for this team before proceeding.

---

## Step 1 — Detect Whether Restore Is Needed

Get the current session ID from the `SessionStart` hook output at the top of
context (format: `SESSION_ID=<uuid>`). Compare with `leadSessionId` in the
team config:

```bash
python3 -c "import json, os; print(json.load(open(os.path.expanduser('~/.claude/teams/$ATM_TEAM/config.json')))['leadSessionId'])"
```

- **Match** → team is already initialized for this session. Proceed directly
  to reading `docs/project-plan.md` and outputting project status.
- **Mismatch or config missing** → follow the full restore procedure in
  `.claude/skills/team-lead/backup-and-restore-team.md`.

---

## Team Lead Responsibilities

After initialization, the team-lead uses these skills to coordinate the team:

| Skill | Trigger |
|-------|---------|
| `/rust-phase-orchestration` | Run a multi-sprint Rust phase where `quality-mgr` owns reviewer selection through `quality-mgr.rust` |
| `/codex-orchestration` | Run phased development where `crap` is the sole developer and `quality-mgr` handles QA coordination |
| `/quality-management-gh` | Multi-pass QA on GitHub PRs; CI monitoring; findings/final quality reports |
| `/sprint-report` | Generate phase status table or detailed report |

> Additional orchestration guides are in `.claude/skills/*/SKILL.md`. Consult
> the relevant skill before starting a new phase or delegating to a teammate.

### Phased Development — MANDATORY

> ⚠️ **For any multi-sprint phased development, `/codex-orchestration`
> or `/rust-phase-orchestration` MUST be used as directed by the user. Using ad-hoc
> coordination instead of these skills leads to process drift, missed
> communications, and inconsistent QA gates.**

**After every session start or context compaction**, if a phase is in progress:

1. Identify which one governs the active phase: `/codex-orchestration` or `/rust-phase-orchestration`. Read only that one unless the user explicitly redirects.
2. If the user explicitly directs a different orchestration surface later, stop and confirm before taking coordination action.
3. Resume execution from the last documented state — do not rely on memory
   alone.

> Skipping this re-read is the primary cause of process drift between sessions.

---

## Task Assignment Protocol

When assigning work to any teammate:

1. **Create or update the task list** — `TaskCreate` or `TaskUpdate` with assignee and description before sending the first message.
2. **Include in the assignment message**:
   - The task and its scope (link to worktree, relevant issues, design docs)
   - Applicable development guidelines (`.claude/skills/team-lead/cross-platform-guidelines.md`, Rust guidelines, etc.)
   - Expected deliverables and acceptance criteria
3. **Use Jinja2 templates** (see `/codex-orchestration` skill) that require:
   - **Immediate ACK** when the agent starts the skill
   - **Intermediate status** notifications at meaningful milestones
   - **Completion notification** with commit/PR reference when done

### Communication Rules

- **No ACK = work is not being done.** If a teammate does not acknowledge within a reasonable
  window, assume the message was not received and follow up (nudge via tmux for Codex agents).
- **Codex agents (`crap`)** do not receive message injection — they only see
  new messages when they check mail after their current task completes. Do not assume they
  received a message until they ACK.

---

## PR and CI Protocol

- **Create the PR as soon as dev completes work and begins self-testing** — before QA starts,
  so CI runs in parallel with the QA review.
- **Immediately after PR creation**, run:
  ```bash
  atm gh monitor pr <NUMBER>
  ```
  to receive CI notifications automatically. Do not wait for the user to ask.
