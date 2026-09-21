# Sprint B4 — Projection, Lineage, and Reconciliation

## Objective and stack

Prove every canonical leaf survives sc-compose rendering and reparse, including explicit one-to-one, split, and combine corpus lineage.

- `gh-stack` branch: `phase-b/04-projection-lineage-reconciliation`
- Relation: `must_follow B3`
- Merge-forward: merge pushed B3 development before every B4 development/fix round; B3 PR merges first.
- Parallel safety: not parallel-safe; B4 consumes and completes B3 authority evidence and produces B5's exact staged tree.

## Projection and lineage contract

A generated canonical-leaf inventory walks validated canonical dumps using RFC 6901 pointers. It classifies content-bearing leaves, authorial lists, set-like projections, and the two transport values governed by the existing provenance transition. Each leaf maps to one named projection value, one template consumption record, and one reparse pointer. Missing leaves, unused projected values, unknown template inputs, repeated claims, or reparse mismatch fail.

Python may validate models, calculate values/digests, and serialize the JSON projection. Complete Markdown—including headings, sections, canonical/provenance/lineage machine blocks, and separators—is assembled only by the verified sc-compose executable and hash-verified selected template set. The subprocess argv, executable digest, template-set digest, input projection digest, output digest, and leaf inventory digest form the render receipt. Existing templates are extended rather than replaced by Python formatting.

`CorpusLineage` implements:

- one-to-one: same `DocumentKey`, every artifact remains in that document;
- split: one input maps to multiple outputs, with each artifact assigned once; one output may retain the input document ID and all additional IDs are explicit proposed identity entries;
- combine: multiple inputs map to an output whose primary origin is explicit; every contributing immutable origin is retained in lineage evidence and the sc-compose-rendered lineage block;
- mixed corpus: the above mappings compose without duplicate input/output document keys or artifact destinations.

All output keys/paths and retired input entries are present in the proposed identity transition. New IDs are caller-supplied, retired IDs cannot be reused, and no artifact may be invented, dropped, duplicated, or change key/content. Reparse reconstructs the lineage block and verifies it against the ledger. Apply extends the existing recoverable journal to replace the staged output set and manifest-selected identity file, then performs idempotent SQLite puts/deletes. A crash resumes by recorded state/hash; path-only moves remain forbidden.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B4-D1 | Deterministic canonical-leaf inventory, projection coverage checker, and render receipt. |
| B4-D2 | Complete sc-compose template projection/reparse support for all five families and lineage metadata, with strict unused/undefined checks. |
| B4-D3 | One-to-one, split, combine, and mixed-corpus lineage planner/validator plus identity transition and retired-ID enforcement. |
| B4-D4 | Corpus staging and existing-journal extension for output set, selected identity path, and idempotent SQLite convergence. |
| B4-D5 | Reparse semantic/provenance/lineage reconciliation producing exactly 100% or a path-qualified failure set. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B4-AC1 | Generated inventories cover every content-bearing leaf of all five canonical families, relationships, extensions, provenance origin, and authorial ordering; only `source_location` and materialization use the documented transition comparison. |
| B4-AC2 | Every leaf is projected, consumed by an inventoried Jinja template, and recovered at the expected pointer after reparse; missing/unused/undefined/duplicate/mutated leaves fail. |
| B4-AC3 | No complete output document can be produced without the pinned sc-compose invocation; tests fail Python heading/section/wrapper assembly or an output lacking matching executable/template/projection receipts. |
| B4-AC4 | One-to-one, split, combine, and mixed lineage cover every input document and assign every input artifact exactly once while preserving keys/content and all immutable origins. |
| B4-AC5 | New/retained/retired document identity rules, proposed-manifest hash, path uniqueness, retired-ID reuse rejection, and rendered lineage-block reparse are deterministic and fail before apply on ambiguity. |
| B4-AC6 | Import/export canonical digests match; render/reparse differs only at the two enumerated transport fields, whose output path, parent/output hash, profile, and template transition independently validate. |
| B4-AC7 | Failure injection at each extended journal state proves restart rollback/roll-forward, selected identity-path use, staged-tree binding, idempotent SQLite retry/delete, lock exclusion, and no false cross-resource atomicity claim. |
| B4-AC8 | Reconciliation reports success only when byte coverage, unit disposition, canonical authority, leaf recovery, persistence, lineage, and transition predicates are each exactly 100%; it never rounds a partial result. |

## Required validation

```sh
which sc-compose && sc-compose --version
python plugins/raptor/scripts/validate_plugin.py --check-cli sc-compose --expected-range '>=1.6.1,<2.0.0' --check-templates --check-inventory
python -m pytest plugins/raptor/tests/migration/test_projection.py plugins/raptor/tests/migration/test_lineage.py plugins/raptor/tests/migration/test_reconciliation.py
python -m pytest plugins/raptor/tests/render plugins/raptor/tests/round_trip plugins/raptor/tests/provenance plugins/raptor/tests/recovery
python plugins/raptor/scripts/migrate_corpus.py --repo-root . --operation-input .raptor/operation-input/migration.json --through reconcile --validate
find plugins/raptor/templates -name '*.j2' -print | sort
git diff --exit-code -- plugins/raptor/templates plugins/raptor/plugin-manifest.json
```

## Traceability and non-closure

- B4-D1–D5 satisfy PB-REQ-004, REQ-RAP-014, and the render/reparse/lineage portion of REQ-RAP-015 and NFR-RAP-008.
- No external validator or site-build execution, compatibility certification, consumer template/profile/fixture, fleet apply, Rust CLI, or Dolt/MySQL.
- A reconciled staged corpus is not yet authorized for replacement; B5 owns trusted compatibility and certification.

## Handoff

B5 receives the immutable staged tree, reconciled ledger, proposed identity transition, and all receipt digests. It must run gates against those exact bytes and cannot regenerate or repair the corpus while certifying it.
