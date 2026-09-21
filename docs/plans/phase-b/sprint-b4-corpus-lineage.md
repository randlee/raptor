# Sprint B4 — Corpus Lineage Planning

## Objective and stack

Close one-to-one, split, combine, and mixed-corpus document/artifact allocation
and identity-transition semantics before any output is rendered.

- `gh-stack` branch: `phase-b/04-corpus-lineage`
- Relation: `must_follow B3`
- Merge-forward: merge pushed B3 development before every B4 development/fix round; B3 PR merges first.
- Parallel safety: not `parallel_safe`; B4 consumes B3's proven canonical set and defines B5's exact output documents and lineage projection.

## Lineage contract

```python
def plan_lineage(
    inputs: tuple[SourceDocument, ...], requested: CorpusLineage | None,
    identity: IdentityManifest,
) -> PlannedCorpus: ...
```

One-to-one retains the input `DocumentKey`. Split assigns every input artifact
exactly once across explicit output documents; one output may retain the input
ID and every additional ID is caller-supplied. Combine names one primary origin
and retains every contributing immutable origin in the lineage record. Mixed
mappings compose these rules. Artifacts may move between documents but cannot
be invented, dropped, duplicated, re-keyed, reordered where order is authorial,
or semantically changed.

The proposed `IdentityManifest` 2.0 transition contains every active output and
irreversible retired input. New IDs are explicit; paths are unique; active and
retired IDs are disjoint; retired IDs cannot be reused. Planning is pure and
non-mutating: it emits output `SourceDocument` values, lineage, and a proposed
identity transition for later projection/reconciliation.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B4-D1 | One-to-one, split, combine, and mixed lineage planner with total document coverage and artifact bijection. |
| B4-D2 | IdentityManifest 2.0 proposed active/retired transition and no-reuse validation. |
| B4-D3 | Primary/contributing immutable-origin retention and deterministic output document/artifact ordering. |
| B4-D4 | Pure `PlannedCorpus` result linked to B3 canonical/persistence receipt digests. |
| B4-D5 | Raptor-owned positive and adversarial lineage/identity test suite. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B4-AC1 | Every input document maps to one or more outputs, every output names its contributors/primary origin, and every input artifact maps to exactly one semantically identical output artifact. |
| B4-AC2 | One-to-one, split, combine, and mixed fixtures preserve all immutable origins and authorial order. |
| B4-AC3 | Unregistered/new/reused-retired IDs, ambiguous primary origin, missing/extra/duplicate/mutated artifacts, path collisions, incomplete mappings, and changes to unrelated identity entries fail deterministically. |
| B4-AC4 | Omitting lineage produces only deterministic one-to-one mappings; split/combine is never inferred from paths, titles, artifact IDs, or content. |
| B4-AC5 | Planning mutates no Markdown, identity file, SQLite database, stage, template, or ledger input. |
| B4-AC6 | Output ordering and lineage/identity digests are identical across repeated runs from the same B3 inputs. |

## Required validation

```sh
python -m pytest schema/tests/migration plugins/raptor/tests/migration/test_lineage.py
python -m pytest schema/tests/models -k 'identity'
python -m mypy --strict schema/src/raptor_schema plugins/raptor/runtime
git diff --exit-code -- schema/json/v1 plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
```

## Traceability and non-closure

- B4-D1–D5 satisfy the corpus-lineage planning portion of PB-REQ-004 and REQ-RAP-015.
- No template projection, rendering, reparse, reconciliation verdict, staging, apply/recovery, compatibility gate, or certification.
- No consumer asset, Rust CLI/SQLx, or Dolt/MySQL implementation.

## Handoff

B5 receives a deterministic `PlannedCorpus`, proposed identity transition, and
lineage digest. It must render those exact planned documents and must not remap
identity or artifacts.
