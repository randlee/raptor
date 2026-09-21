# Sprint B3 — Lossless Byte and Persistence Proof

## Objective and stack

Prove that every authorized Markdown byte and every canonical value has replayable authority through canonical JSON, SQLite import, and SQLite export.

- `gh-stack` branch: `phase-b/03-lossless-byte-persistence-proof`
- Relation: `must_follow B2`
- Merge-forward: merge pushed B2 development before every B3 development/fix round; B2 PR merges first.
- Parallel safety: not parallel-safe; it extends B2's ledger and supplies B4's canonical/leaf baseline.

## Accounting contract

Extend the versioned `SourceProfile` boundary with a content-unit and proof result, implemented by the existing built-in profile and required from external migration-capable profiles:

```python
def segment(self, source: SourceInput) -> tuple[SourceContentUnit, ...]: ...
def canonicalize_with_proof(
    self, parsed: ParsedDocument, units: tuple[SourceContentUnit, ...]
) -> CanonicalizationResult: ...
```

Intervals are zero-based half-open UTF-8 byte offsets. For each exact source byte string, ordered units begin at zero, are contiguous/non-overlapping, and end at byte length. Whitespace/comments are units. A unit ID and byte hash are recomputed from bytes; caller-supplied IDs are not trusted. Unsupported units and invalid UTF-8 produce rejected ledger entries and prevent import/apply.

`CanonicalizationResult` carries the existing `SourceDocument`, canonical/preserved transformation records, and typed derivations. The reconciler resolves JSON Pointers against the canonical dump, reruns every allowlisted exact-version rule from recorded bytes or verified authoritative input, and rejects missing/extra pointer outputs or digest mismatch. Every content-bearing canonical leaf has exactly one authority: one or more source units through one transformation, or one derivation. Presentation-only units still require exactly one preserved/explicit presentation disposition; they are never absent from coverage.

The existing SQLite store is called through its public API. B3 adds digest-linked import/export receipts containing document/artifact keys, canonical document digests, row/projection counts, database schema/model versions, and upstream digest. Export is canonicalized again and must exactly match import except no fields are permitted to differ at this boundary.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B3-D1 | Migration-capable source-profile segmentation/proof protocol extension and built-in Raptor implementation. |
| B3-D2 | Shared accounting/replay runtime for byte partitions, transformations, derivations, JSON Pointer authority, and exact coverage. |
| B3-D3 | Existing Markdown→canonical JSON and JSON→SQLite→JSON operations instrumented with B1 boundary receipts; no duplicate parser/store. |
| B3-D4 | Positive and adversarial byte/transform/derivation/persistence fixtures from Raptor-owned Markdown, including Unicode and all unit kinds. |
| B3-D5 | Deterministic ledger continuation whose downstream records bind the B2 ingress digest. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B3-AC1 | Every accepted non-empty file has exact contiguous interval coverage from byte 0 through byte length, stable unit IDs/hashes, and one disposition per unit; CRLF, multibyte UTF-8, trailing whitespace, comments, tables, code fences, and link definitions are accepted cases, while an empty source is a deterministic pre-import rejection. |
| B3-AC2 | Unsupported syntax, invalid UTF-8, gap, overlap, reorder, altered kind/bounds/hash, duplicate disposition, and relabeled content-bearing unit fail before SQLite mutation. |
| B3-AC3 | Every canonical leaf has exactly one replayable source or derivation authority; pointer stuffing, unrelated/extra transform output, stale rule versions, non-finite values, missing authority input, and digest mutation fail reconciliation. |
| B3-AC4 | Identity, configuration, source digest, and generated materialization values use typed derivations whose authoritative input hash and exact rule re-execute successfully. |
| B3-AC5 | Existing canonical JSON and SQLite APIs preserve exact normalized documents, keys, authorial order, relationships, extensions, and provenance; import/export canonical digests and counts match. |
| B3-AC6 | `batch` and `store` reference modes remain explicit; unresolved/duplicate cross-document or cross-repository keys roll back the complete SQLite write and produce ledger diagnostics. |
| B3-AC7 | Every receipt includes the prior receipt digest; deleting, replacing, or reordering one receipt invalidates all dependent reconciliation without source/database mutation. |

## Required validation

```sh
python -m pytest schema/tests/migration plugins/raptor/tests/migration/test_accounting.py plugins/raptor/tests/migration/test_persistence_proof.py
python -m pytest plugins/raptor/tests/operations schema/tests/storage
python -m mypy --strict schema/src/raptor_schema plugins/raptor/runtime
git diff --exit-code -- schema/json/v1 plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
rg -n '\bNFT\b|sqlx|dolt://' schema/src plugins/raptor/runtime/accounting.py plugins/raptor/tests/migration && exit 1 || true
```

## Traceability and non-closure

- B3-D1–D5 satisfy PB-REQ-003 and the import/persistence portion of REQ-RAP-015 and NFR-RAP-008.
- No full Markdown document assembly, template rewrite, staged output, reparse comparison, split/combine apply, migration CLI/agent activation, external gate execution, or certification.
- No replacement of existing canonical/SQLite APIs, Rust CLI, Dolt/MySQL, or consumer fixture.

## Handoff

B4 receives one canonical document set, byte/accounting ledger, and exact SQLite export receipt. It may not reinterpret source bytes or weaken authority to make rendering reconcile.
