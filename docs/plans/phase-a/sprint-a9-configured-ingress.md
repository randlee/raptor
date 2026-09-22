# Sprint A9 — Configured Ingress and Batch Loss Report

## Objective

Extend the existing Python ingress operations so a repository-root invocation
uses validated `.raptor/` configuration to process an authorized Markdown
inventory and emit a deterministic per-path report.

- Branch: `phase-a/09-configured-ingress`
- Stack relation: `must_follow A8`
- Merge-forward trigger: A8 development is pushed; merge A8 into A9 before each development or fix round.
- PR-completion trigger: A8 PR merges first.

## Scope boundary

A9 extends existing configuration loading, identity registration, and
Markdown→JSON / JSON→SQLite operations. Its batch mode is hosted by the
existing `plugins/raptor/scripts/markdown_to_json.py` thin wrapper, with
orchestration in `plugins/raptor/runtime/operations.py`; the wrapper gains
explicit `--config` and `--report` flags for the config-driven inventory and
its report. It adds one batch invocation path and one JSON report; it does not
add a parser, a store, a second rendering path, or a consumer-specific profile.
Adding a differently named wrapper is out of scope because it would escape the
CI `Enforce Phase A5 exclusions` wrapper allowlist. Configuration remains
consumer-owned below `.raptor/`.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A9-D1 | Manifest-selected scan, routing, and identity loading using the published Pydantic configuration models. | Direct runtime tests for valid, missing, duplicate, overlapping, and unauthorized paths. |
| A9-D2 | Batch mode on `plugins/raptor/scripts/markdown_to_json.py`, selected by explicit `--config` and `--report` flags and orchestrated by `plugins/raptor/runtime/operations.py`; it accepts manifest-selected configuration, processes the sorted authorized inventory, and uses existing JSON→SQLite persistence. | One documented script/agent invocation and batch integration tests. |
| A9-D3 | Versioned Pydantic loss/diagnostic report model under `schema/src/raptor_schema`, with generated JSON Schema under `schema/json/v2`, containing path, document identity, selected route/profile, canonical digest, SQLite outcome, field count, relationship count, and origin/materialization provenance digests. Its generated schema uses the same schema-contract tests and `Verify deterministic schema vendor` drift gate as canonical models. | Stable fixture assertions, generated-schema/drift assertions, and deterministic repeated-run comparison. |
| A9-D4 | Consumer-neutral usage documentation for configuration, identity registration, validate mode, apply mode, and report retention. | Documentation check and no consumer fixture added to Raptor. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A9-AC1 | The batch operation reads only paths selected by exactly one validated scan source and route; absent or invalid configuration authorizes no scan. |
| A9-AC2 | Every selected path is imported or appears once with a structured diagnostic; an unregistered or conflicting identity fails closed. |
| A9-AC3 | Every imported document validates through existing Pydantic models and is persisted through the existing SQLite store. |
| A9-AC4 | Repeated validate-mode runs over unchanged inputs emit byte-identical ordered reports. |
| A9-AC5 | The report distinguishes field, relationship, and provenance results; it never silently omits an unsupported file or value. |
| A9-AC6 | The implementation extends the existing operations and thin adapters only; no consumer asset, Rust code, Dolt code, or parallel parser/store is added. |
| A9-AC7 | The report validates as the versioned Pydantic model, its generated JSON Schema is present under `schema/json/v2`, and schema-contract plus deterministic vendor checks fail on model/schema/vendor drift. |

## Authoritative validation commands

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/schema/src" python3 -m pytest -q \
  schema/tests/models/test_repository_config_manifest.py \
  schema/tests/models/test_scan_config.py \
  schema/tests/models/test_routing_config.py \
  schema/tests/models/test_ingress_report.py \
  schema/tests/json_schema/test_generated_schemas.py \
  plugins/raptor/tests/operations/test_batch_ingress.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/schema/src" python3 -m pytest -q \
  schema/tests/models/test_identity.py
python3 plugins/raptor/scripts/validate_plugin.py --check-inventory --check-vendor
python3 plugins/raptor/scripts/vendor_schema.py --check
```

## Traceability

| Deliverable | Requirements |
|---|---|
| A9-D1, A9-D2 | PA-REQ-010, PA-REQ-011, PA-REQ-012, REQ-RAP-013 |
| A9-D3 | NFR-RAP-008, REQ-RAP-015 |
| A9-D4 | PA-NFR-001, PA-NFR-003, PA-NFR-006 |

## Risks

| Risk | Mitigation |
|---|---|
| A batch scan reads undeclared files | Resolve and validate the full inventory before parsing any source. |
| A report hides a partial result | Require exactly one terminal report entry for every selected path. |
| Batch code duplicates existing operations | Make batch orchestration call the existing ingress and store APIs. |

## Non-closure

- A9 does not prove SQLite export or rendered Markdown equivalence; A10 owns that proof.
- A9 does not run an external consumer corpus; A12 owns that proof.
- Deferred: byte-unit ledgers, transformation/derivation proofs, trust policy, tool-bundle sandboxing, corpus split/combine lineage, certification engines, and multi-resource apply/recovery orchestration.
