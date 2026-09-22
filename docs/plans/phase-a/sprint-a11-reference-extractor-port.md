# Sprint A11 — Reference Extractor Port

## Objective

Replace the invented Markdown grammar with a typed, repository-neutral port of
the working reference extractor. Make the existing Markdown-to-JSON and runtime
operations consume that profile directly, migrate the canonical model and
SQLite store safely, and establish local anonymized parser/render conformance.
The separate A12 sprint executes the external-corpus proof.

- Branch: `phase-a/11-reference-extractor-port`
- Stack relation: `must_follow A10`
- Merge-forward trigger: merge current `develop` and A10 before implementation
  and each fix round.
- PR-completion trigger: A10 merges first.

The reference checkout is read only. Its prose, identifiers, paths, templates,
configuration, fixture values, and reports never enter Raptor. Raptor stores
only invented, domain-neutral fixtures and structural contracts.

## Reference facts and normative parser contract

The reference index contains 783 artifacts. Every index record has these ten
top-level fields: `id`, `title`, `type`, `status`, `domain`,
`document_metadata`, `source`, `content`, `relationships`, and
`subsections`. Observed status spellings are Draft, Proposed, Active,
Approved, Deprecated, and Superseded. Those facts define the A11 compatibility
shape; the consumer keeps the pinned extractor revision, index, and real inputs
used by A12.

The built-in profile identifier is `reference-markdown/v1`. Routing selects it
explicitly; unknown or mixed profile input is diagnosed with the selected
document identity and never falls back to the deleted native grammar.

| Input / condition | Required parser behavior | Output / diagnostic |
|---|---|---|
| `## REQ|NFR|ADR-<scope>-<four digits>: <title>` | Recognize level-two artifact headings in source order; preserve source spelling and title. | Requirement, NFR, or ADR artifact with source location. |
| `#### TEST...: <title>` | Recognize level-four test headings within a test-plan document. | Ordered test-case/traceability extension; it never overwrites the parent test plan. |
| Initial bold metadata preamble | Parse supported key/value entries before body sections; preserve unknown entries in an extension. | `document_metadata` and artifact metadata; malformed pairs receive a stable diagnostic. |
| Nested Markdown sections | Preserve heading level, title, Markdown body, HTML/summary if emitted, order, and source range. | Ordered `subsections` and `content`, with no semantic flattening. |
| Identifier ranges or cross-references | Preserve raw source token and context, then resolve only when a target is unique in the defined lookup order. | Resolved triple target, contextual target, or unresolved/ambiguous relationship plus diagnostic. |
| A selected Markdown file with no recognized artifact | End with a deterministic terminal diagnostic, not a silent empty import. | `RAP-MD-NO-ARTIFACT` diagnostic. |
| Invalid UTF-8, malformed heading/preamble, unsupported status, duplicate heading, or nested invalid heading | Fail closed for that selected document and report stable code, severity, path, and location. | One or more deterministic diagnostics; batch result remains terminal. |

Resolution order is: explicit document-qualified target; source document;
repository-wide unique target; otherwise retain the raw reference and emit an
ambiguity or unresolved diagnostic. Lists retain source order; maps serialize
with canonical JSON ordering. Missing and empty values are distinct.
Markdown/HTML are compared byte-for-byte after UTF-8 decoding; only LF,
terminal newline, and the documented application-date token are normalizable
during template comparison.

## Canonical mapping, relationship, and identity contract

One reference index record maps to one Raptor artifact inside a
`SourceDocument` envelope. The envelope remains the canonical top-level JSON
unit; it supplies repository/document identity, provenance, materialization,
schema version, and ordered membership that are not supplied by an index record.

### v2 artifact representation

v2 replaces the v1 family payload union with a source-faithful discriminated
`ReferenceArtifact` union. Every variant has exactly the ten required source
fields plus `artifact_type`, and `artifact_type` remains one of requirement,
non-functional requirement, architecture decision, design document, or test
plan. The existing named family models become thin typed aliases/projections of
that union, not containers that require v1 synthetic fields. `SourceDocument`
continues to expose a five-family discriminated artifact union; public parser,
store, renderer, and JSON-schema APIs accept that v2 union only.

`ReferenceArtifact` serializes the ten source fields verbatim in a
`source_profile` object and supplies optional `raptor_projection` fields only
when derived from present source content. No `statement`, acceptance criterion,
measurement, decision context/consequence, component, objective, or scope is
required or synthesized. Sc-compose receives the v2 artifact plus ordered
source-profile sections and renders from that data. Fixtures must prove each
former v1-required family field may be absent, v2 validation succeeds, and the
artifact renders and reparses without loss.

| Reference field | Raptor destination | Requiredness / preservation rule |
|---|---|---|
| `id` | `artifact.artifact_id` | Required; locally unique only within `(repository_id, document_id)`. |
| `title`, `type`, `status`, `domain` | Base artifact fields and source-profile extension | Required; retain source spelling. `type` maps to one of the five canonical families. |
| `document_metadata` | Envelope metadata/profile extension | Required object; unknown keys round trip unchanged. |
| `source` | Immutable origin plus source-profile extension | Required; retain path-independent locations and source representation. |
| `content`, `subsections` | Family body plus ordered source-profile extension | Required; preserve sequence, Markdown, HTML/summary when present, and missing-vs-empty state. |
| `relationships` | Relationship record and raw-reference extension | Required list; see resolution contract below. |
| Absent index fields | No synthetic source field | Never invent a statement, acceptance criterion, measurement, or quality value. Raptor-only fields are optional extensions. |

Artifact identity becomes the immutable triple `(repository_id, document_id,
artifact_id)`. `ArtifactKey`, `ArtifactTarget`, `ArtifactRelationship`,
diagnostics, sort keys, resolver APIs, store/list/query APIs, and JSON schema
must carry the document component. A v2 relationship is a discriminated
`resolved`, `contextual`, `unresolved`, or `ambiguous` record. All variants
contain source identity triple, raw token, context, relation label, and
deterministic ordinal. Resolved/contextual variants also contain target identity
triple and resolution basis; unresolved/ambiguous variants contain a diagnostic
key and no target foreign key. Canonical sorting is source ordinal then raw
token then target triple; duplicate source edges preserve ordinal and are never
collapsed. Typed projection edges derived from a family remain separate from
source-profile raw edges and point to the same target triple only when
resolution succeeds. A relationship is therefore either:

1. an explicit resolved triple target;
2. an implicit target resolved by the documented lookup order, retaining its raw
   token and resolution basis; or
3. an unresolved/ambiguous raw target with a diagnostic, retained without an
   invalid foreign key.

SQLite v2 has triple primary/foreign keys for artifacts and resolved relationship
source/target columns, plus a `source_relationships` table for every raw edge
and an `unresolved_relationships` table keyed by source triple and ordinal.
The latter stores raw token, context, relation label, resolution basis, and
diagnostic key with no invalid foreign key. Required indexes cover document
membership, triple target lookup, and raw-reference diagnostics. Tests cover
same-document, explicit cross-document, unique contextual, ambiguous,
missing/deleted, and batch/store resolution cases.

## Schema and migration decision

This is a canonical-contract breaking change. A11 publishes canonical model
and JSON Schema version `2.0.0`, generates `schema/json/v2`, adds SQLite
migration `0002_document_scoped_artifacts.sql`, and synchronizes the vendored
schema package. It updates the current-schema constant and accepted-version
rules, generated schema registry, bootstrap/vendor constants, SQLite metadata,
all `ArtifactKey` dependents, profile boundaries, and public script/runtime
interfaces.

The migration runner must recognize a populated v1 database, run the upgrade in
one transaction, and leave the original database unchanged on failure. A v1
store could not contain cross-document duplicate local IDs because its global
uniqueness constraint rejected them; its representable documents, memberships,
canonical JSON, and resolved relations are preserved by backfilling their known
document identity. Duplicate-local-ID fixtures are imported only after the
upgrade and prove the v2 contract. Rollback of a failed transaction, reopening
the original v1 store, a successful one-document v1 fixture upgrade, and a
post-upgrade duplicate-ID import are tested.

There is no dual-write or permanent v1 runtime. A11 reruns the model, schema,
storage, plugin, A9 ingress, and A10 round-trip suites against v2 before the
new parser becomes the only built-in profile.

## A1 reversals and replacement decisions

| Prior decision / acceptance | A11 replacement |
|---|---|
| A1 native level-three em-dash headings and inline fields. | Delete native grammar/profile/fixtures; use the level-two colon and level-four test-heading contract above. Supersedes A1-D3 and parser portions of A1-AC2/A1-AC4. |
| A1 three-digit ID grammar and `TST` test-plan prefix. | Validate four-digit source IDs and `TEST` headings; retain source spelling. Supersedes A1-D3/A1-AC2 identifier rules. |
| A1 lower-case lifecycle normalization and additional lifecycle values. | Preserve the six source status spellings; unsupported values diagnose, never coerce. Supersedes A1-D3/A1-AC2. |
| A1 synthetic statement/acceptance/measurement payloads. | The ten emitted fields are the source contract. Raptor-only values are optional extensions only when actually present. Supersedes A1-D3/A1-D5/A1-AC2/A1-AC4. |
| A1/A2 repository-plus-artifact key and duplicate rejection. | Use the immutable identity triple and ambiguity-preserving relationship resolution. Supersedes A1-D6/A1-AC5/A1-AC11 and affected A2/A10 assumptions. |
| A1 narrowed relationship taxonomy. | Preserve source relationship context/raw tokens and typed resolutions without guessing an owner. Supersedes A1-D3/A1-D6/A1-AC15 narrowing. |

## Scope boundary

A11 is Python/Pydantic/parser/template work only. It reuses
`plugins/raptor/scripts/markdown_to_json.py` and
`plugins/raptor/runtime/operations.py`; it adds no Rust, SQLx, Dolt,
framework, or consumer adapter. A9 remains configured ingress and reporting;
A10 remains SQLite/export/traceability proof. Their callers change only for
the v2 model, document-scoped identity, and replacement parser.

The five-family contract is explicit: REQ, NFR, and ADR map directly from
recognized headings. The 783-record index/digest domain is exactly those direct
REQ/NFR/ADR records; it does not claim design or test-plan records. Design and
test-plan records are a separate, route-selected document population. Their
counts, if present in an external inventory, are attested separately from 783.

A route that permits exactly `design_document` or `test_plan` selects the
document-level grammar; the parser never guesses a family from a path. The first
nonblank line must be a level-one title, followed by the bold metadata preamble
and ordered nested sections. The preamble supplies local ID and status; all
other keys are preserved. A design document has no child-heading requirement.
A test plan may contain zero or more level-four `TEST...: <title>` headings,
which become ordered test evidence with their body/subsections and locations.
Missing level-one title/ID/status, a wrong route family, or a malformed test
heading emits stable diagnostics. A11 proves this contract using invented
design/test fixtures, not copied consumer templates or content.

The active template-copy utility is an external template-tree oracle, not a
Raptor JSON renderer or implementation dependency. Its structural contract is
UTF-8 recursive copy, ignored paths, literal `{{KEY}}` replacement, and supplied
template-version/application-date tokens. A12 uses it only to attest the
consumer materialized template-tree manifest/digest and token rules. Raptor
Jinja templates are independently authored and run through sc-compose; A11
proves canonical JSON→Markdown→JSON equality with an artifact-to-output manifest
that permits the documented file/layout split. A12 separately runs the consumer
parser/site compatibility gates against Raptor-rendered Markdown.

## Plugin-surface inventory

Implementation must update the registered agents and template inventory below
where their v1 contract changes; none may keep a parallel native parser or
v1-only identity assumption.

| Surface | A11 obligation |
|---|---|
| `agents/markdown-validate.md`, `agents/markdown-json-import.md` | Route and report `reference-markdown/v1` diagnostics and v2 documents. |
| `agents/json-validate.md`, `agents/json-sqlite-import.md`, `agents/sqlite-validate.md` | Validate v2 identity, raw/resolved relationships, and migration outcome. |
| `agents/sqlite-json-export.md`, `agents/json-markdown-export.md`, `agents/migration-round-trip.md` | Export triple-key artifacts, render v2 JSON, and report five-family reparse equality. |
| `templates/requirement.md.j2`, `templates/non-functional-requirement.md.j2`, `templates/architecture-decision.md.j2` | Render every content-bearing v2 field for direct heading families. |
| `templates/design-document.md.j2`, `templates/test-plan.md.j2` | Render ordered sections, design metadata, test-plan coverage/traceability, and test-heading evidence. |
| `runtime/operations.py`, `scripts/markdown_to_json.py`, `scripts/import_sqlite.py`, `scripts/export_sqlite.py`, `scripts/json_to_markdown.py` | Preserve the existing public-operation sequence while replacing only parser/model/key assumptions. |

## Authoritative deliverables

| ID | Deliverable | Evidence |
|---|---|---|
| A11-D1 | Port `reference-markdown/v1` into the existing profile/runtime path and delete the prior native grammar/fixtures. | Strict typing and invented parser fixtures for valid and all specified failure modes. |
| A11-D2 | Publish v2 Pydantic models, canonical JSON Schema, field map, document-scoped identity, relationship resolution, and v2 SQLite projection. | Schema/model drift tests; triple-key, resolver, and relation conformance tests. |
| A11-D3 | Implement and test atomic v1→v2 SQLite migration plus fail-closed/recovery behavior. | Populated-v1 upgrade, rollback, reopen, preservation, and vendor synchronization tests. |
| A11-D4 | Implement five-family routing, design/test-plan mapping, and sc-compose Jinja rendering from v2 JSON. | Invented fixtures prove metadata, sections, ranges, traceability, test headings, artifact/output manifest, and render/reparse equality. |
| A11-D5 | Implement the consumer-neutral A12 attestation Pydantic model and v2 JSON Schema: algorithm/version, pinned-coordinate field, expected count, aggregate and per-record digest fields, direct-index comparison allowlist, template-tree manifest/digest, and count/digest-only failure report. | Generated schema, Pydantic validation, and deterministic digest tests using invented data. |
| A11-D6 | Re-close A1/A9/A10 affected contract tests and update operations, phase plan, traceability, and A12 command/interface placeholders. | Complete v2 regression suite and documented A12 prerequisite interface. |

## Implementation sequence

1. Lock invented index-contract fixtures, diagnostic codes, canonicalization,
   and the field-by-field envelope mapping (A11-D1/D2).
2. Port parsing and remove the native grammar. Every A9-selected file reaches
   an imported or diagnosed terminal result (A11-D1).
3. Migrate keys, targets, resolver APIs, diagnostics, SQLite v2 DDL, and A9/A10
   callers as one transactionally tested contract change (A11-D2/D3).
4. Add five-family routes and independently authored Jinja/sc-compose rendering
   (A11-D4), then the neutral attestation format (A11-D5).
5. Re-run all affected historical suites, publish the A12 handoff, and update
   traceability (A11-D6). A12—not A11—then runs the external corpus oracle.

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A11-AC1 | The only built-in Markdown grammar is versioned `reference-markdown/v1`; routing has no fallback. Valid, malformed, no-match, duplicate, invalid-encoding, nested-heading, metadata, status, relationship, mixed-profile, and unknown-profile cases have deterministic results and locations. |
| A11-AC2 | A v2 `SourceDocument` envelope and artifact mapping retain every ten source fields, all six observed statuses, source order, missing-vs-empty state, provenance, and document membership without synthetic source data. |
| A11-AC3 | The triple identity is implemented across JSON, public APIs, diagnostics, SQLite, and queries. Same-document, explicit cross-document, contextual, ambiguous, and missing relationships meet the resolution contract; no repeated local label overwrites data. |
| A11-AC4 | A populated v1 SQLite database upgrades atomically to v2 or fails closed without mutation. Successful migration preserves canonical JSON, memberships, resolvable relations, and queryability; failure rolls back and the v1 store reopens. |
| A11-AC5 | A9 ingress and A10 proof use the v2 parser/model/key contract with no parallel parser, store, renderer, or wrapper. All affected model/schema/storage/plugin/A9/A10 tests re-close. |
| A11-AC6 | Invented five-family fixtures prove all content-bearing v2 fields render through sc-compose and reparse to equal canonical JSON, except the documented materialization transition; an artifact/output manifest makes any allowed file/layout split explicit. |
| A11-AC7 | The attestation contract is reproducible: it identifies extractor/index coordinate, canonicalization algorithm/version, 783 direct-index expected count, separate optional design/test population counts, per-record and aggregate digest, comparison allowlist, template-tree manifest/digest, and count/digest-only failure output. |
| A11-AC8 | Raptor contains no external consumer source, prose, identifier, path, template, configuration, fixture, or report. Changed fixtures and reports are allowlist-reviewed; the consumer-owned denylist/signature gate runs only in its checkout and exports counts/digests only. |
| A11-AC9 | No Rust, SQLx, Dolt, new framework, fleet migration, or external apply/replacement automation is added. |

## Authoritative validation commands

The code sprint creates these named tests before declaring completion.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/schema/src" python3 -m pytest -q \
  schema/tests/models/test_reference_contract.py \
  schema/tests/models/test_reference_identity.py \
  schema/tests/models/test_reference_relationship_resolution.py \
  schema/tests/storage/test_sqlite_store.py \
  schema/tests/storage/test_sqlite_v1_to_v2_migration.py \
  schema/tests/storage/test_sqlite_traceability_queries.py \
  schema/tests/json_schema/test_generated_schemas.py \
  plugins/raptor/tests/profiles/test_reference_markdown.py \
  plugins/raptor/tests/operations/test_batch_ingress.py \
  plugins/raptor/tests/round_trip/test_reference_template_parity.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/schema/src" python3 -m mypy --strict \
  schema/src/raptor_schema plugins/raptor/runtime plugins/raptor/scripts
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/schema/src" python3 -m raptor_schema.generate \
  --check --output schema/json/v2
git diff --exit-code -- schema/json/v2
python3 plugins/raptor/scripts/vendor_schema.py --check
python3 plugins/raptor/scripts/validate_plugin.py --check-inventory --check-vendor --check-templates
```

The consumer runs the A12-only oracle after the A12 evidence-model/schema code
lands: direct extraction over configured roots, 783/783 order-aware direct-index
comparison under the attestation allowlist, zero blocked entries,
SQLite/export/render/reparse, template-tree manifest check, its parser/site
gate on Raptor output, and consumer privacy gate. ATM receives only
expected/actual counts and allowed digests.

## Traceability

| Requirement | A11 owner / evidence |
|---|---|
| PA-REQ-001, PA-REQ-003 | A11-D1/D2: v2 five-family source-profile contract and generated schema. |
| PA-REQ-002 | A11-D2/D3: triple identity, provenance, resolution, and SQLite migration. |
| PA-REQ-004 | A11-D1: deterministic source diagnostics and no silently skipped selected documents. |
| PA-REQ-005, PA-REQ-006 | A11-D2/D3/D6: v2 SQLite/runtime path and historical regression closure. |
| PA-REQ-007, PA-REQ-008 | A11-D4: five sc-compose templates and reparse equality on neutral fixtures. |
| PA-NFR-001 | A11-D5/D6: invented fixtures, attestation handoff, and Raptor-side allowlist review. |
| PA-NFR-003 | A11-AC9: Python/Pydantic only; no Rust or SQLx. |
| PA-NFR-004, PA-NFR-005 | A11-D1/D2/D5: deterministic ordering, v2 schema, and digest protocol. |
| PA-NFR-006 | A11-D6: one stacked reviewed implementation PR and A12 handoff. |
| REQ-RAP-013 | A11-D1/D6: A9 configured ingress uses the replacement parser. |
| REQ-RAP-014, REQ-RAP-015 | A11-D2/D3/D4/D6: v2 SQLite/export, templates, migration, and local lossless proof. |
| REQ-RAP-016 | A11-D5/D6 prepare the external evidence interface; A12 owns execution. |
| NFR-RAP-008 | A11-D1/D2/D5: deterministic diagnostics, resolution, and attestation evidence. |

## Risks and non-closure

| Risk | Mitigation |
|---|---|
| Rich source content is simplified. | Field map preserves metadata, source representation, relationships, subsections, and locations. |
| Repeated labels corrupt SQL relations. | Triple keys, raw-reference retention, and deterministic ambiguity diagnostics. |
| Migration damages an existing store. | Transactional upgrade, fail-closed preflight, rollback, and reopen tests. |
| External parity or privacy evidence leaks data. | Neutral local fixtures; external comparison and signature scan remain consumer-owned; only counts/digests cross ATM. |

Deferred: A12 external proof and compatibility-gate execution, fleet migration,
consumer apply/replacement automation, Dolt/MySQL, Rust/SQLx, byte-unit ledgers,
and formats not represented by the reference extractor.
