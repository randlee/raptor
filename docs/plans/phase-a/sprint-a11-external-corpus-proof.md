# Sprint A11 — External Corpus Proof

## Objective

Run the completed Raptor loop against the authorized external consumer corpus,
retain a reproducible evidence report, and confirm that rendered Markdown is
accepted by that repository's validator and web consumer tests.

- Branch: `phase-a/11-external-corpus-proof`
- Stack relation: `must_follow A10`
- Merge-forward trigger: A10 development is pushed; merge A10 into A11 before each development or fix round.
- PR-completion trigger: A10 PR merges first.

## Scope boundary

Execution occurs only in the p3-documentation checkout
`/Users/randlee/Documents/p3-documentation-worktrees/integration/raptor` on
branch `integration/raptor` at commit
`e2833c1f45476b2a067483eab8ef8138d7d0e02b`, by `arch-p3@p3-doc`.
Raptor receives an evidence report attached to the A11 PR; no p3 Markdown,
configuration, profile, template, or test fixture enters this repository.

Before the loop, `arch-p3@p3-doc` creates consumer-owned `.raptor/raptor.toml`,
scan/routing configuration, and identity registration in that checkout using
the A9 documentation. The configuration selects all authorized Markdown and
does not authorize `.build/` or `.raptor/` generated state.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A11-D1 | Consumer-owned `.raptor/` ingress configuration and registered document identities in the external checkout. | Configuration validation and identity-registration output retained outside Raptor. |
| A11-D2 | Batch Markdown→JSON→SQLite→JSON→sc-compose→Markdown run using the A9/A10 public operations. | Per-path and aggregate loss report, before/after tree digests, and canonical/SQLite/render results. |
| A11-D3 | Explicit diagnostics for every unsupported input. | The six unrecognized test Markdown files appear once each as diagnosed items; none is silently skipped. |
| A11-D4 | External compatibility gates on rendered output. | Extractor report digest, companion audit result, and web-test result. |
| A11-D5 | A compact evidence attachment on the A11 PR. | Loss report plus extractor-report and before/after-tree digests; no consumer source content. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A11-AC1 | The report identifies the pinned checkout commit and includes every authorized path as imported, rendered, or explicitly diagnosed. |
| A11-AC2 | Every imported document has zero loss for fields, artifact order, relationships, identity, immutable origin, and materialization provenance. |
| A11-AC3 | The corpus includes approximately 57 REQ plus 4 NFR, approximately 57 ADR, approximately 43 design documents, and 27 extractor-recognized test plans; all six unrecognized test files are explicit diagnostics. |
| A11-AC4 | `python3 scripts/extract-requirements.py --project-root . --output-dir .build` reports 202 scanned documents with zero errors and zero warnings on rendered output. |
| A11-AC5 | `python3 scripts/qa-audit.py --hook-mode` passes with `total_errors=0`, and `PYTHONPATH=src/web python3 -m pytest src/web/tests -q` passes after installing `src/web/requirements.txt`. |
| A11-AC6 | The A11 PR receives only the evidence attachment: loss report, extractor-report digest, and before/after tree digests. No consumer Markdown or fixture is copied into Raptor. |

## Authoritative validation commands

```sh
cd /Users/randlee/Documents/p3-documentation-worktrees/integration/raptor
git rev-parse HEAD
python3 /Users/randlee/Documents/github/raptor/plugins/raptor/scripts/run_agent.py migration-round-trip \
  --client codex --repository-root . --params '{"config":".raptor/raptor.toml","database":".raptor/raptor.sqlite","report":".build/raptor-loss-report.json","apply":true}'
python3 scripts/extract-requirements.py --project-root . --output-dir .build
python3 scripts/qa-audit.py --hook-mode
python3 -m pip install -r src/web/requirements.txt
PYTHONPATH=src/web python3 -m pytest src/web/tests -q
```

## Traceability

| Deliverable | Requirements |
|---|---|
| A11-D1, A11-D2 | REQ-RAP-013, REQ-RAP-015, NFR-RAP-008 |
| A11-D3 | REQ-RAP-013, REQ-RAP-015 |
| A11-D4, A11-D5 | REQ-RAP-016, PA-NFR-001 |

## Risks

| Risk | Mitigation |
|---|---|
| External corpus layout differs from the generic configuration examples | Keep configuration and profiles consumer-owned; report unsupported items instead of changing canonical models. |
| A test file is silently excluded | Require the six unrecognized test files as named diagnostic outcomes. |
| Evidence leaks consumer source into Raptor | Attach only reports and hashes; review the PR diff before upload. |

## Non-closure

- A11 is a consumer-owned proof, not an external-repository apply or replacement operation.
- No static site build exists in this execution environment; the extractor is the primary compatibility gate and web tests are the secondary gate.
- Deferred: byte-unit ledgers, transformation/derivation proofs, trust policy, tool-bundle sandboxing, corpus split/combine lineage, certification engines, and multi-resource apply/recovery orchestration.
