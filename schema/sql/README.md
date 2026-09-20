# SQL persistence mapping

Raptor has one semantic schema: the versioned Pydantic models and canonical JSON
contract. SQL files are dialect projections, not alternate domain models.

| Model value | SQLite ownership and projection |
|---|---|
| `SourceDocument.schema_version` | `source_documents.schema_version`; verified against reconstructed JSON |
| `SourceProvenance.origin` | complete canonical `origin_json`; repository/document identity is also projected into the composite key |
| `SourceProvenance.materialization` | complete canonical `materialization_json`; current path is projected into `current_path` |
| each canonical artifact | complete canonical `artifact_json`; ID, type, and status are indexed columns |
| document artifact order | `document_artifacts.ordinal`, unique within a composite `DocumentKey`; `artifact_count` and `membership_sha256` preserve the expected ordered membership independently of surviving rows |
| artifact relationships | unique semantic edges in `artifact_relationships` for typed composite targets and `artifact_uri_relationships` for URI targets |
| design dependencies and test verification keys | typed rows in `artifact_relationships` with `depends_on` and `verifies` relations; when a derived edge collides with an explicit relationship, the single edge retains the explicit description |

Canonical JSON owns all optional values, extensions, source locations, and
family-specific payloads. SQL `NULL` is used only for an optional relationship
description. On load, the adapter structurally validates the JSON and rejects
any disagreement with scalar, membership, ordinal, or relationship projections.
Reads also fail closed when a repository, document, artifact, membership, or
typed relationship endpoint has been corrupted behind foreign-key enforcement.
Document and fragment JSON use the same canonical encoder, including key order,
compact separators, omitted `None` fields, finite-number checks, and negative-zero
normalization.

Replacement and deletion are document-keyed transactions. Source relationship
rows are replaced, removed artifacts are deleted only when no external inbound
reference exists, and retained artifact identities are updated in place. A path
change is accepted only through a valid rendered provenance transition. There
is no path-only operation.

The table/key/foreign-key contract and JSON checks in
`sqlite/0001_initial.sql` are the SQLite authority. The `ArtifactStore`
protocol and conformance helper are dialect-neutral; connection handling,
`json_valid`, foreign-key pragmas, and transaction syntax are SQLite-specific.
The wheel build force-includes that authoritative file as a package resource;
there is no second checked-in DDL copy.
