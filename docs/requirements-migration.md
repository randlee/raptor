# Phase A Round-Trip Completion Requirements

Status: owned by Phase A sprints A9–A12. These requirements complete the
existing Python/Pydantic/SQLite/sc-compose path; they do not introduce a new
migration platform or modify the Rust CLI.

## REQ-RAP-013 — Configured batch ingress

Raptor shall discover Markdown only through the validated `.raptor/` manifest,
scan, routing, and identity configuration, then invoke the existing
Markdown→JSON and JSON→SQLite operations for each authorized file.

Acceptance: the batch result is deterministic; each selected path is imported
or has a structured diagnostic; no undeclared path is read; and each emitted
document validates with the published Pydantic model.

Owner: A9.

## REQ-RAP-014 — SQLite export and Markdown projection

Raptor shall recover a selected SQLite document as canonical Pydantic JSON and
generate Markdown only through the existing sc-compose template set.

Acceptance: identical canonical JSON renders identical Markdown bytes; every
content-bearing schema field is rendered or explicitly reported; and rendering
is followed by source-profile reparse.

Owner: A10.

## REQ-RAP-015 — Lossless round trip and traceability

Raptor shall prove, for every supported family, the following semantic loop:

```text
Markdown → JSON → SQLite → JSON → sc-compose → Markdown → JSON
```

Acceptance: the reparsed canonical document equals the imported canonical
document after only the already-defined materialization transition; the loss
report is zero for the ten record fields, source Markdown, artifact order,
relationships, identity, immutable origin, and materialization provenance.
SQLite must retain queryable emitted relationship types forward and reverse,
plus document/artifact membership and provenance projections.

Owner: A10, A11, A12.

## REQ-RAP-016 — External rendered-output compatibility

Raptor shall demonstrate the same loop on the authorized external consumer
corpus and run that repository's validator and declared secondary gates against
the rendered output.

Acceptance: each authorized source has a zero-loss result; all five families
are represented; the consumer validator and declared secondary gates are clean; and the
consumer supplies the evidence report without contributing fixtures or source
documents to Raptor.

Owner: A12.

## NFR-RAP-008 — Deterministic, fail-closed evidence

Each batch result shall record the selected path, identity, canonical digest,
SQLite result, rendered-output result, field coverage, provenance result, and
relationship result. Missing configuration, an unsupported value, a failed
comparison, or a non-zero loss report fails the operation.

Owner: A9, A10, A11, A12.

## Deferred scope

The following are explicitly deferred: byte-unit ledgers, transformation or
derivation proofs, trust policy, tool-bundle sandboxing, corpus
split/combine lineage, certification engines, and multi-resource
apply/recovery orchestration. Dolt, SQLx, and Rust CLI work are also out of
scope.
