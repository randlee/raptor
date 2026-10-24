# Repository Quality Policy

This file contains repository-specific QA policy. Reusable agents and skills
must read this file rather than embedding repository names, commands,
interfaces, approval authorities, or temporary architectural exceptions in
their own prompts. The orchestration templates name this file as
`policy_path`.

Adapted from atm-core `.claude/project/quality-policy.md` (develop
`92f670c31`). Rules are kept aligned with atm-core; only repository facts
differ.

## Repository Baseline

- Default comparison branch: `develop`
- Requirements index: `docs/requirements.md` (REQ ids inline, e.g.
  `REQ-RAP-0001`)
- Architecture index: `docs/architecture.md`; ADRs are
  `docs/adr/ADR-NNN-<slug>.md`, indexed by `docs/adr/INDEX.md`
- Project plan: `docs/project-plan.md`
- Team protocol: none yet; the `codex-orchestration` and
  `atm-bd-orchestration` skills are the protocol
- Developer roster: `.atm.toml` and the ATM roster (`atm members`) are
  authoritative for live identities; there is no roster file.

## Reviewer Policy

- Initial implementation review (sprint QA-1): `req-qa`, `arch-qa`,
  `ruthless-boundary-qa`, `rust-qa-agent`, `rust-best-practices-agent`, and
  `rust-service-hardening-agent` (the last returns a structured skip while
  raptor has no service crates)
- Fix verification is separate from sprint QA rounds 1–2: dispatch only the
  agent necessary to confirm the specific fix, normally the filing reviewer.
  Lock it to the original finding and acceptance criterion. No automatic
  req-qa/arch-qa/rust-qa or screening panel, no full sweep, and no new findings.
  The verifier runs necessary focused checks and confirms original-finding
  closure. Required CI remains a separate merge requirement.
- Plan review QA-1: `plan-scope-reviewer`, `req-qa`, `arch-qa`,
  `ruthless-boundary-qa`, `rust-best-practices-agent`, and `ceremony-qa`.
  `plan-scope-reviewer` judges the plan's shape against the architecture's
  boundary map: the wave table, the critical path and width it recomputes
  from the bead graph, `owned_paths` disjointness within a wave, and the
  contract artifact named by every `must_follow` edge. Its assignment is
  rendered with `plan-scope-reviewer-assignment.json.j2` (codex-orchestration
  for a plan in markdown, atm-bd-orchestration for a plan in beads) over the
  same plan files as `req-qa` and `arch-qa`, plus the phase plan or root
- Plan review QA-2 and later is fix verification: dispatch only the filing
  reviewer of each carried finding, locked to that finding and its original
  acceptance criterion. `req-qa`, `arch-qa` and `plan-scope-reviewer` are not
  re-run unless one of them filed a carried finding, and then only for its own
  ids. No screening panel, no full sweep, and no new findings. The lead
  recomputes the critical path after each round of rulings (below). Plan QA
  is capped at 3 rounds (`plan_qa_cycle_limit`); a round that leaves only
  minor findings reports `PASS — minor fixes required, no re-QA`
- Plan review rulings: the remedy for shared types, shared files or a shared
  version baseline is to hoist the artifact into the contract or integration
  sprint (plan guidelines, "Ownership And Dependency Relations"), never an
  edge. `quality-mgr` lists every finding whose remedy would add a
  `must_follow` edge, an ordering rule or a merge-order clause as a proposed
  `hoist` ruling for the lead (`quality-mgr.md`, "Hoist Rulings"), in the
  same way as its proposed `rejected: ceremony` rulings. The lead accepts an
  edge only with a recorded reason naming the artifact that could not be
  hoisted, and recomputes the wave table's critical path, width and sprint
  count after each round of rulings. An edge that lengthens the critical
  path is the user's ruling, not the lead's: the lead puts the proposed edge,
  the artifact and the new critical path to the user and records the answer
  in the ruling; without that record the round is redone. The baseline
  critical path is the architecture's layer count (contract, the layers
  `docs/architecture.md` defines, integration); a plan is not held to a fixed
  number of waves, but every wave past that baseline carries a user-approved
  reason
- `ceremony-finding-screen`: every sprint or plan QA round that has
  findings, over all of them, before the report is posted; never on fix
  verification, which files no new findings
- Phase-end review: the initial implementation set plus `flaky-test-qa`
- Run `flaky-test-qa` earlier when tests changed or instability is suspected
- `schema-reviewer`: in plan review and phase-ending review whenever a
  governed interface (below) is in scope
- Every QA round, plan or sprint, requires an open PR; the rendered report
  is posted to it every round

## Validation Policy

These are the commands CI runs (`.github/workflows/ci.yml`) and the values
of `lint_command` / `test_command` in `.claude/agents/registry.yaml`.

- Lint: `cargo fmt --check --all && cargo clippy --all-targets --all-features -- -D warnings`
- Tests: `cargo test && python3 -m pytest -q tests`
- Phase-end validation: `cargo build` plus the lint and test commands above;
  quality-mgr passes them to `rust-qa-agent` as `artifact_commands` on every
  `phase_end` assignment and never runs them in the foreground. There is no
  release preflight yet.

## Plan Naming

Everything in file names, branch names, front matter `id` values and
template variables is lower case. Prose may write "Phase C" and "C.4".

| Thing | Form | Example |
|---|---|---|
| Phase id | next unused letter (or letter pair), lower case | `c` |
| Sprint id | `<phase>-<n>`, `n` from 1 | `c-4` |
| Plan directory | `docs/plans/phase-<phase>/` | `docs/plans/phase-c/` |
| Phase plan | `docs/plans/phase-<phase>/phase-<phase>-plan.md` | `phase-c-plan.md` |
| Sprint doc | `docs/plans/phase-<phase>/sprint-<phase>-<n>-<slug>.md` | `sprint-c-4-record-writer.md` |
| Plan branch | `plan/phase-<phase>`, PR to `develop` | `plan/phase-c` |
| Phase branch | `integrate/phase-<phase>`, cut from `develop` | `integrate/phase-c` |
| Sprint branch | `sprint/<phase>-<n>-<slug>` | `sprint/c-4-record-writer` |
| Fix layer | `fix/<phase>-<n>-<slug>`; phase-level: `fix/<phase>-<slug>` | `fix/c-4-qa1` |
| Bead prefix | `rap` | `rap-4ij` |
| Worktree | `../raptor-worktrees/<branch>` | `../raptor-worktrees/sprint/c-4-record-writer` |

The full rule set is "Naming" in
`.claude/skills/plan-hardening/sprint-planning-guidelines.md`. Stack
mechanics: the `sc-gh-stack` and `sc-gh-stack-view` skills.

## Governed Interfaces

Raptor has no governed interfaces yet. When the record schema
(`crates/raptor-schema`, ADR-004) or the CLI's JSON output contract ships,
add it here with its versioning rule and evidence paths, and retarget
`schema-reviewer` (`.claude/agents/schema-reviewer.md`, currently written for
atm-core) to it. Until then `schema-reviewer` is not dispatched.

## Repository Exceptions

- ADR ids are in file names under `docs/adr/` (`ADR-001-*.md`) and are not
  `## ADR-...` sections of `docs/architecture.md`; REQ ids are inline in
  `docs/requirements.md`. `validate-plan` matches an id against document
  content and file names (manifest `docs.*`). Pre-migration ids
  `ADR-RAP-NNNN` are listed as aliases in `docs/adr/INDEX.md`.
- Existing sprint docs (phases a and b, before beads orchestration) carry no
  `requirements` / `adrs` front matter lists; do not raise missing-list
  findings for them.
- Reviewer prompts copied from atm-core still name atm-core crates, ADRs and
  `just` recipes; treat those as examples, and apply this file's commands
  and paths.
