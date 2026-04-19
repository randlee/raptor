---
name: sprint-report
version: 1.0.0
description: Generate a sprint status report for the current phase. Default is --table.
---

# Sprint Report Skill

Build fenced JSON and pipe to the Jinja2 template. `mode` controls table vs detailed.

## Usage

```
/sprint-report [--table | --detailed]
```

Default: `--table`

---

## Data Source

> ⚠️ **MUST EDIT — Data Source**
> Replace with the appropriate PR listing command for this repo:
> - ATM repos: `atm gh pr list` — single call, returns all open PRs with CI and merge state
> - Standard repos: `gh pr list --state all --limit 20` + `gh pr checks <PR_NUMBER>` for CI detail

Use the data source to populate `sprint_rows` and `integration_row`. Only drill into individual
`gh run view` calls if you need failure details for a specific job.

## Render Command

The template path is relative — must run from the **main repo root** (not a worktree).

```bash
cd "${CLAUDE_PROJECT_DIR:-$(git worktree list | head -1 | awk '{print $1}')}"
echo '<json>' > /tmp/sprint-report.json
sc-compose render .claude/skills/sprint-report/report.md.j2 --var-file /tmp/sprint-report.json
```

## --table (default)

```json
{
  "mode": "table",
  "sprint_rows": "| P1.1 | ✅ | ✅ | 🏁 | #10 |\n| P1.2 | ✅ | ✅ | 🌀 | #11 |",
  "integration_row": "| **integrate/phase-1** | | — | 🌀 | — |"
}
```

## --detailed

```json
{
  "mode": "detailed",
  "sprint_rows": "Sprint: P1.1  Description\nPR: #10\nQA: PASS ✓\nCI: Merged to integrate/phase-1 ✓\n────────────────────────────────────────\nSprint: P1.2  Description\nPR: #11\nQA: PASS ✓ (iter 2)\nCI: Running (1 pending)",
  "integration_row": "Integration: integrate/phase-1 → develop\nCI: Running — pending P1.3"
}
```

## Icon Reference

| State | DEV | QA | CI |
|-------|-----|----|----|
| Assigned | 📥 | 📥 | |
| In progress | 🌀 | 🌀 | 🌀 |
| Done/Pass | ✅ | ✅ | ✅ |
| Findings | 🚩 | 🚩 | |
| Fixing | 🔨 | | |
| Blocked | | | 🚧 |
| Fail | | | ❌ |
| Merged | | | 🏁 |
| Ready to merge | | | 🚀 |
