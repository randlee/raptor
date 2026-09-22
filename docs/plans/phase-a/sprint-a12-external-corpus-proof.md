# Sprint A12 — External Corpus Proof

## Objective

Run the completed Raptor loop in a consumer-owned checkout, retain a
reproducible consumer-neutral evidence report, and confirm that the consumer's
declared compatibility gates accept rendered Markdown.

- Branch: `phase-a/12-external-corpus-proof`
- Stack relation: `must_follow A11`
- Merge-forward trigger: A11 development is pushed; merge A11 into A12 before each development or fix round.
- PR-completion trigger: A11 PR merges first.

## Scope boundary

The consumer's designated agent executes this sprint in the consumer's checkout;
Raptor team-lead coordinates through ATM. The consumer retains its own runbook
containing checkout path, pinned commit, commands, and expected counts. Raptor
never stores that runbook or consumer source, configuration, profiles, templates,
or fixtures.

Before the loop, the consumer agent creates consumer-owned `.raptor/`
configuration and registers document identities using A9 documentation. The
configuration selects authorized Markdown and excludes generated/control state.

A11 lands the v2 consumer-neutral evidence model/schema defined by A11-D5
before A12 begins. The consumer executes the external proof against that merged
contract and attaches a validated instance to the A12 PR. The consumer never
implements Raptor schema code.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A12-D1 | Consumer-owned `.raptor/` ingress configuration and registered document identities. | Configuration validation and identity-registration output retained in the consumer checkout. |
| A12-D2 | Batch Markdown→JSON→SQLite→JSON→sc-compose→Markdown run using A9/A10 public operations through the A11 reference extractor. | Per-path pipeline state records and aggregate loss report plus before/after corpus-tree digests. |
| A12-D3 | Execute the A11 attestation protocol against the consumer's pinned extractor/index coordinate. The consumer chooses and retains the coordinate; its report exposes only contract version, algorithm/version, expected and actual count, allowed comparison paths, aggregate digest, permitted per-record digests, and count/digest-only failures. | Exact expected/actual artifact count, aggregate comparison result, and no source content or paths. |
| A12-D4 | Validate and attach an instance of the A11 Raptor-owned Pydantic evidence model and generated schema. | Pinned coordinate digest, aggregate/count attestation, aggregate terminal-outcome counts, loss fields, per-family counts, primary-gate result, secondary-gate results, and evidence-model/schema validation. |
| A12-D5 | Explicit diagnostics for unsupported inputs and compatibility-gate execution on rendered output. | One final state per input, stage results, primary-gate report digest, and secondary-gate results. |
| A12-D6 | Compact evidence attachment on the A12 PR. | Evidence JSON only; no consumer source content. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A12-AC1 | Every authorized path has one ordered pipeline record: `selected` → `imported` → `exported` → `rendered` → `reparsed` → final `completed`, or final `diagnosed` at the failing stage. Import and render are stage results, never mutually exclusive terminal states. |
| A12-AC2 | Every `completed` document has zero loss for fields, artifact order, relationships, identity, immutable origin, and materialization provenance. |
| A12-AC3 | Unsupported inputs appear as explicit diagnostics and are never silently skipped. |
| A12-AC4 | The evidence JSON records an approved repository/commit coordinate digest, before/after corpus-tree digests, aggregate terminal-outcome counts, per-family counts reported by the run, and the A9/A10 loss fields; it contains no source path, identifier, or prose. |
| A12-AC5 | The consumer's declared primary compatibility gate reports zero errors and zero warnings on rendered output; every declared secondary gate passes. |
| A12-AC6 | The evidence records exact counts for every family present in the authorized inventory. Five-family coverage is proven by A11 neutral fixtures; a family absent from the authorized inventory is reported as zero rather than making a valid external proof impossible. |
| A12-AC7 | Only the evidence JSON is attached to the A12 PR; consumer Markdown, configuration, profiles, templates, fixtures, and runbook remain in the consumer repository. |
| A12-AC8 | A12 is not assignable while any placeholder remains; before assignment this command block is replaced with the exact commands as merged in A11. |
| A12-AC9 | The attached evidence validates against the Raptor-owned, consumer-neutral Pydantic evidence model and its generated JSON Schema, composed from the A9/A10 report-model family. |
| A12-AC10 | Direct Raptor extraction is 783/783 field-equal to the pinned index under the A11 comparison allowlist, has zero blocked entries, and has an aggregate attestation digest. The former consumer adapter is not used or required. |
| A12-AC11 | The external template-copy utility attests its materialized template-tree manifest/digest and token rules. Separately, Raptor Jinja/sc-compose output meets the A11 artifact/output-manifest and reparse-equality contract, and the consumer parser/site gates accept that output. |
| A12-AC12 | The consumer-owned privacy scan and all declared compatibility gates pass; its ATM/PR evidence contains only approved counts, contract coordinates, and digests. |

## Authoritative validation commands — template pending A9/A10 merge

```sh
# A9 fixes this batch-ingress CLI contract; A12 invokes it without redefining it.
python3 plugins/raptor/scripts/markdown_to_json.py --repo-root <consumer-root> \
  --config <consumer-config> --report <consumer-loss-report> --apply
# A10 fixes these SQLite-export/render proof CLI contracts; A12 invokes them without redefining them.
python3 plugins/raptor/scripts/export_sqlite.py --repo-root <consumer-root> \
  --database <consumer-sqlite> --repository-id <consumer-repository-id> \
  --document-id <consumer-document-id> --output <consumer-canonical-json> \
  --report <consumer-loss-report> --apply
python3 plugins/raptor/scripts/json_to_markdown.py --repo-root <consumer-root> \
  --input <consumer-canonical-json> --output <consumer-rendered-markdown> \
  --database <consumer-sqlite> --report <consumer-loss-report> --apply
# Run the primary and secondary compatibility gates from the consumer-owned runbook.
```

Before A12 assignment, A12-AC8 replaces the remaining consumer-owned flag
values with the exact A11 merged contracts. The consumer runbook executes
its own compatibility commands without copying them into Raptor.

Raptor-owned contract tests cover the evidence model and generated schema:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/schema/src" python3 -m pytest -q \
  schema/tests/models/test_ingress_report.py \
  schema/tests/models/test_external_evidence_report.py \
  schema/tests/json_schema/test_generated_schemas.py
python3 plugins/raptor/scripts/vendor_schema.py --check
```

## Traceability

| Deliverable | Requirements |
|---|---|
| A12-D1, A12-D2 | REQ-RAP-013, REQ-RAP-015, NFR-RAP-008 |
| A12-D3, A12-D4, A12-D5 | REQ-RAP-015, REQ-RAP-016, NFR-RAP-008 |
| A12-D6 | PA-NFR-001, REQ-RAP-016 |

## Risks

| Risk | Mitigation |
|---|---|
| Consumer conventions leak into Raptor | Keep the runbook, configuration, and assets in the consumer repository; attach evidence JSON only. |
| An unsupported input is silently excluded | Require one explicit `diagnosed` outcome for every unsupported path. |
| Evidence cannot reproduce a result | Bind consumer repository ID, pinned commit digest, tree digests, outcomes, and gate results. |

## Non-closure

- A12 is a consumer-owned proof, not an external-repository apply or replacement operation.
- A12 does not define consumer commands, paths, counts, profiles, templates, or gate implementations; the consumer runbook owns them.
- Deferred: byte-unit ledgers, transformation/derivation proofs, trust policy, tool-bundle sandboxing, corpus split/combine lineage, certification engines, and multi-resource apply/recovery orchestration.
