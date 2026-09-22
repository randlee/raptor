# Sprint A11 — External Corpus Proof

## Objective

Run the completed Raptor loop in a consumer-owned checkout, retain a
reproducible consumer-neutral evidence report, and confirm that the consumer's
declared compatibility gates accept rendered Markdown.

- Branch: `phase-a/11-external-corpus-proof`
- Stack relation: `must_follow A10`
- Merge-forward trigger: A10 development is pushed; merge A10 into A11 before each development or fix round.
- PR-completion trigger: A10 PR merges first.

## Scope boundary

The consumer's designated agent executes this sprint in the consumer's checkout;
Raptor team-lead coordinates through ATM. The consumer retains its own runbook
containing checkout path, pinned commit, commands, and expected counts. Raptor
never stores that runbook or consumer source, configuration, profiles, templates,
or fixtures.

Before the loop, the consumer agent creates consumer-owned `.raptor/`
configuration and registers document identities using A9 documentation. The
configuration selects authorized Markdown and excludes generated/control state.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A11-D1 | Consumer-owned `.raptor/` ingress configuration and registered document identities. | Configuration validation and identity-registration output retained in the consumer checkout. |
| A11-D2 | Batch Markdown→JSON→SQLite→JSON→sc-compose→Markdown run using A9/A10 public operations. | Per-path and aggregate loss report plus before/after corpus-tree digests. |
| A11-D3 | Versioned consumer-neutral evidence JSON, authored as a Raptor-owned Pydantic evidence model under `schema/src/raptor_schema`, with generated JSON Schema under `schema/json/v1`. It composes the A9/A10 report-model family; the consumer produces an instance, but Raptor owns the schema and its schema-contract and deterministic-vendor drift gates. | Consumer repository ID, pinned consumer commit digest, per-path terminal outcome, loss fields, per-family counts, primary-gate result, secondary-gate results, and evidence-model/schema validation. |
| A11-D4 | Explicit diagnostics for unsupported inputs and compatibility-gate execution on rendered output. | One diagnosed outcome per unsupported input; primary-gate report digest and secondary-gate results. |
| A11-D5 | Compact evidence attachment on the A11 PR. | Evidence JSON only; no consumer source content. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A11-AC1 | Every authorized path has exactly one terminal outcome: `imported`, `rendered`, or `diagnosed`. |
| A11-AC2 | Every imported document has zero loss for fields, artifact order, relationships, identity, immutable origin, and materialization provenance. |
| A11-AC3 | Unsupported inputs appear as explicit diagnostics and are never silently skipped. |
| A11-AC4 | The evidence JSON records consumer repository ID, pinned consumer commit digest, before/after corpus-tree digests, per-path outcomes, per-family counts reported by the run, and the A9/A10 loss fields. |
| A11-AC5 | The consumer's declared primary compatibility gate reports zero errors and zero warnings on rendered output; every declared secondary gate passes. |
| A11-AC6 | All five canonical families appear in the run evidence. |
| A11-AC7 | Only the evidence JSON is attached to the A11 PR; consumer Markdown, configuration, profiles, templates, fixtures, and runbook remain in the consumer repository. |
| A11-AC8 | A11 is not assignable while any placeholder remains; before assignment this command block is replaced with the exact commands as merged in A9 and A10. |
| A11-AC9 | The attached evidence validates against the Raptor-owned, consumer-neutral Pydantic evidence model and its generated JSON Schema, composed from the A9/A10 report-model family. |

## Authoritative validation commands — template pending A9/A10 merge

```sh
# A9 fixes this batch-ingress CLI contract; A11 invokes it without redefining it.
python3 plugins/raptor/scripts/markdown_to_json.py --repo-root <consumer-root> \
  --config <consumer-config> --report <consumer-loss-report> --apply
# A10 fixes these SQLite-export/render proof CLI contracts; A11 invokes them without redefining them.
python3 plugins/raptor/scripts/export_sqlite.py --repo-root <consumer-root> \
  --database <consumer-sqlite> --repository-id <consumer-repository-id> \
  --document-id <consumer-document-id> --output <consumer-canonical-json> \
  --report <consumer-loss-report> --apply
python3 plugins/raptor/scripts/json_to_markdown.py --repo-root <consumer-root> \
  --input <consumer-canonical-json> --output <consumer-rendered-markdown> \
  --database <consumer-sqlite> --report <consumer-loss-report> --apply
# Run the primary and secondary compatibility gates from the consumer-owned runbook.
```

Before A11 assignment, A11-AC8 replaces the remaining consumer-owned flag
values with the exact A9/A10 merged contracts. The consumer runbook executes
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
| A11-D1, A11-D2 | REQ-RAP-013, REQ-RAP-015, NFR-RAP-008 |
| A11-D3, A11-D4 | REQ-RAP-015, REQ-RAP-016, NFR-RAP-008 |
| A11-D5 | PA-NFR-001, REQ-RAP-016 |

## Risks

| Risk | Mitigation |
|---|---|
| Consumer conventions leak into Raptor | Keep the runbook, configuration, and assets in the consumer repository; attach evidence JSON only. |
| An unsupported input is silently excluded | Require one explicit `diagnosed` outcome for every unsupported path. |
| Evidence cannot reproduce a result | Bind consumer repository ID, pinned commit digest, tree digests, outcomes, and gate results. |

## Non-closure

- A11 is a consumer-owned proof, not an external-repository apply or replacement operation.
- A11 does not define consumer commands, paths, counts, profiles, templates, or gate implementations; the consumer runbook owns them.
- Deferred: byte-unit ledgers, transformation/derivation proofs, trust policy, tool-bundle sandboxing, corpus split/combine lineage, certification engines, and multi-resource apply/recovery orchestration.
