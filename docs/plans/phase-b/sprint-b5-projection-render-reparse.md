# Sprint B5 — Projection, Render, and Reparse

## Objective and stack

Prove every canonical and lineage leaf from B4 survives verified sc-compose
document assembly and source-profile reparse.

- `gh-stack` branch: `phase-b/05-projection-render-reparse`
- Relation: `must_follow B4`
- Merge-forward: merge pushed B4 development before every B5 development/fix round; B4 PR merges first.
- Parallel safety: not `parallel_safe`; B5 consumes the immutable B4 plan and establishes B6's rendered/reparsed corpus proof.

## Projection contract

```python
def inventory_canonical_leaves(document: SourceDocument) -> CanonicalLeafInventory: ...
def project_document(
    document: SourceDocument, *, lineage: DocumentLineage,
    profile: SourceProfile, template_set: TemplateSet,
) -> ProjectionReceipt: ...
def verify_render_reparse(
    expected: SourceDocument, rendered: RenderedDocument, reparsed: SourceDocument,
    *, lineage: DocumentLineage, receipt: ProjectionReceipt,
) -> RenderReparseReceipt: ...
```

The inventory walks deterministic canonical dumps using RFC 6901 pointers. It
classifies content-bearing leaves, authorial lists, set-like projections, the
lineage block, and the two transport values governed by the existing provenance
transition. Each leaf maps to one named projection value, one template
consumption record, and one reparse pointer. Missing leaves, unused projected
values, unknown template inputs, repeated claims, or reparse mismatch fail.

Python may validate models, calculate values/digests, and serialize the JSON
projection. Complete Markdown—including headings, sections, canonical,
provenance, and lineage blocks, and separators—is assembled only by the verified
sc-compose executable and hash-verified selected template set. The render receipt
binds executable, argv, template-set, leaf-inventory, lineage, projection, and
output digests.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B5-D1 | Deterministic canonical/lineage leaf inventory and projection coverage checker for all five families. |
| B5-D2 | Complete sc-compose projection/template support with strict unused/undefined-value enforcement. |
| B5-D3 | Render receipt binding executable, argv, templates, lineage, projection, inventory, and output bytes. |
| B5-D4 | Source-profile reparse verifier covering canonical equality, lineage-block recovery, and the provenance/materialization transition. |
| B5-D5 | Raptor-owned five-family, split/combine, leaf, lineage, and provenance mutation suites. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B5-AC1 | Inventories cover every content-bearing canonical and lineage leaf, relationships, extensions, immutable origins, and authorial ordering; only `source_location` and materialization use transition comparison. |
| B5-AC2 | Every leaf is projected, consumed by an inventoried Jinja template, and recovered at the expected pointer after reparse; missing, unused, undefined, duplicated, reordered, or mutated leaves fail. |
| B5-AC3 | No complete output document can be produced without pinned sc-compose; tests reject Python heading/section/wrapper assembly and outputs lacking matching receipts. |
| B5-AC4 | Import/export canonical digests match, and render/reparse differs only at the enumerated transport fields whose path, parent/output hash, profile, and template transition independently validate. |
| B5-AC5 | Reparsed one-to-one/split/combine lineage equals the B4 plan, including contributing origins and artifact destinations. |
| B5-AC6 | Same canonical JSON, lineage, profile, template set, and sc-compose version produce identical inventory/projection/output/receipt digests. |

## Required validation

```sh
which sc-compose && sc-compose --version
python plugins/raptor/scripts/validate_plugin.py --check-cli sc-compose --expected-range '>=1.6.1,<2.0.0' --check-templates --check-inventory
python -m pytest plugins/raptor/tests/migration/test_projection.py plugins/raptor/tests/migration/test_render_reparse.py
python -m pytest plugins/raptor/tests/render plugins/raptor/tests/round_trip plugins/raptor/tests/provenance
find plugins/raptor/templates -name '*.j2' -print | sort
git diff --exit-code -- plugins/raptor/templates plugins/raptor/plugin-manifest.json
```

## Traceability and non-closure

- B5-D1–D5 satisfy PB-REQ-004 / REQ-RAP-014 and the render/reparse lineage portion of REQ-RAP-015.
- No final reconciliation verdict, immutable corpus stage, apply/recovery, external compatibility evidence, migration CLI/agent activation, or certification.
- No consumer asset, Rust CLI/SQLx, or Dolt/MySQL implementation.

## Handoff

B6 receives B2–B5 receipts plus exact rendered/reparsed bytes and documents. It
may reconcile and stage them but may not reinterpret source bytes, remap lineage,
or rerender output.
