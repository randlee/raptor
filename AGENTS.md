# Repository Working Rules

## Mandatory worktree policy

- **Always use `/sc-git-worktree` to create every task, feature, fix, documentation, planning, or release worktree.** Do not create worktrees or task branches manually when the skill is available.
- **Always keep the primary Raptor repository checkout on `develop`.** Never switch the primary checkout to a task branch.
- Perform all task edits, commits, tests, pushes, and PR preparation in the dedicated `/sc-git-worktree` worktree created from `develop`.
- Before starting work, verify that the primary checkout is on `develop` and that the task worktree has the intended branch and base.
- If the primary checkout contains task work or is on another branch, preserve the work first, relocate it to a dedicated `/sc-git-worktree`, then restore the primary checkout to `develop`. Never discard user work to enforce this policy.
- Use the `/sc-git-worktree` update, scan, cleanup, or abort workflows for worktree lifecycle operations.


## Honest Work, No Ceremony (binding on agents and humans)

Goal: working, deployable capability. Process serves it and never becomes the product.

- **Process artifacts** (certificates, ledgers, dashboards, matrices, meta-reports, speculative checks) need four things to exist: a named consumer, the feature it gates, the observed defect class that justifies it, and a deletion condition. Missing any of these → don't create it. Test: if running code branches on it, it's product. If only humans or reports read it, it's process and needs the four things. Writing code just to flip that answer is itself the pathology. Exception: a minimal integrity/recovery control (crash-recovery state, provenance snapshot) that prevents a named evidence-loss or corruption mode.
- **Real code + real tests in the same unit of work.** Forbidden: faked tests, mocks/fixtures presented as live proof, weakened assertions, regenerating goldens to force green, hard-coded success paths, placeholder macros in commits, editing the spec instead of implementing it, narrowing scope while claiming full success.
- **No self-certification.** An independent verifier closes the work, citing evidence at an exact revision. In solo sessions, re-verify by re-running, and state what wasn't independently verified.
- **Typed refusal beats fabrication but is worth less than real capability.** Work that ends only in a refusal stays open and says so.
- **Null results are successes** ("checked X, found no material increment"). Unsupported claims are worse than silence.
- **Metrics** predeclare their denominator and countermetric. Agreement between agents can raise confidence but is never independent evidence. Never silence stderr in commands that produce evidence.
- **Name pathologies when they occur:** gate self-weakening, proof-class inflation, golden regeneration, tolerance widening, suppression-pragma laundering, refusal farming, follow-up laundering. The full catalog and countermeasures are in the `just-say-no-to-process-porn-and-ceremony` skill. Ask the operator for it if you can't find it.
