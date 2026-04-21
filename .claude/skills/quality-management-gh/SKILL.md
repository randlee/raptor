---
name: quality-management-gh
version: 1.1.0
description: Reusable QA orchestration skill for GitHub PRs. Use for multi-pass QA, CI monitoring with `atm gh monitor`, one-shot PR reporting with `atm gh pr report`, and template-driven findings/final quality reports.
---

# Quality Management (GitHub)

This skill defines a reusable quality-management workflow for teams that run QA across one or more passes before merge.

## Scope

Use this skill when you need to:
- run QA in multiple passes (`IN-FLIGHT`, `FAIL`, `PASS`),
- monitor CI progression for a PR,
- publish structured findings to PR + ATM,
- publish a final QA closeout report on PASS.

This skill is intentionally generic. Team-specific teammate names, branch policy, and background-agent ownership stay in the team's `quality-mgr` agent prompt.

## Required QA Status Contract

Every QA update (ATM and PR) must include:
- sprint/task identifier
- branch, commit, PR number
- verdict (`PASS | FAIL | IN-FLIGHT`)
- finding counts by severity (`blocking`, `important`, `minor`)
- blocking IDs + concise summaries
- next required action + owner
- merge readiness (`ready | not ready`) + reason

Use fenced JSON for machine-readable status payloads:

```json
{
  "sprint": "P1.2",
  "task": "issue-42",
  "branch": "feature/p1-s2-slug",
  "commit": "abc1234",
  "pr": 57,
  "verdict": "FAIL",
  "findings": {
    "blocking": 1,
    "important": 2,
    "minor": 1
  },
  "blocking_ids": ["QA-001"],
  "next_action": "Fix failing validation",
  "owner": "crap",
  "merge_readiness": "not ready",
  "merge_reason": "Blocking findings remain"
}
```

## QA Lifecycle (Multi-Pass)

1. Initial pass: usually `FAIL` with findings.
2. Fix passes: `IN-FLIGHT` or `FAIL` while fixes are in progress.
3. Final pass: `PASS` with final quality report and merge recommendation.

Do not treat QA as single-shot.

## CI Monitoring

Use daemon-backed monitoring for CI progression:

1. Ensure plugin configured:
- `atm gh`
- `atm gh status`

2. Start/attach CI monitor for a PR:
- `atm gh monitor pr <PR> --start-timeout 120`

3. Inspect lifecycle/availability during QA:
- `atm gh monitor status`
- `atm gh status pr <PR>`

If monitoring cannot start, include the failure in QA status and proceed with one-shot PR report data.

## One-Shot PR Report Generation

Use:
- `atm gh pr report <PR> --json`

Use report JSON to populate findings/final template fields (checks summary, review decision, merge readiness signals).

## Findings Report to PR (FAIL / IN-FLIGHT)

Template: `.claude/skills/quality-management-gh/findings-report.md.j2`

For `FAIL` — post as blocking review:
```bash
sc-compose render --root .claude/skills/quality-management-gh \
  --file findings-report.md.j2 \
  --var-file <vars.json> | gh pr review <PR> --request-changes --body-file -
```

For `IN-FLIGHT` — post as comment (do not oscillate review states):
```bash
sc-compose render --root .claude/skills/quality-management-gh \
  --file findings-report.md.j2 \
  --var-file <vars.json> | gh pr comment <PR> --body-file -
```

Fallback when `sc-compose` is unavailable:
```bash
gh pr review <PR> --request-changes --body-file <fallback.md>
```

`<vars.json>` must be a flat JSON map (`string -> string`). See template frontmatter for required variables.

## Final Quality Report to PR (PASS Closeout)

Template: `.claude/skills/quality-management-gh/quality-report.md.j2`

```bash
sc-compose render --root .claude/skills/quality-management-gh \
  --file quality-report.md.j2 \
  --var-file <vars.json> | gh pr review <PR> --approve --body-file -
```

Fallback when `sc-compose` is unavailable:
```bash
gh pr review <PR> --approve --body-file <fallback.md>
```

Use the final template only for `PASS` closeout.

## PR Update Conventions

- First QA pass posts detailed findings with `FAIL` → must use `--request-changes`
- Fix-pass updates revise status and open findings → use comment updates
- Final pass posts `PASS` closeout → must use `--approve`

This creates the default lifecycle: blocking review on findings, then approval on successful re-review so the PR can merge.

Never overwrite history silently — each update should be clearly timestamped and tied to a pass number. Rendered reports must include a fenced JSON block for machine parsing.

## ATM Coordination Protocol

For each task:
1. Immediate acknowledgement
2. Execute QA work
3. Send completion/status summary
4. Receiver acknowledgement

No silent processing.
