# Canonical field ownership

The Sprint A1 plan is the normative field/type/constraint matrix. This mapping
identifies the owner used by the executable models.

| Classification | Fields | Owner |
|---|---|---|
| canonical envelope | schema version; artifact type, ID, title, status, summary | `SourceDocument`, `ArtifactBase` |
| family payload | statement, measurement, decision, components, interfaces, test cases and criteria | the five family models |
| provenance | immutable origin; current path/hash/operation/profile/template transition | `SourceProvenance` |
| identity | repository/document and repository/artifact composite keys | `DocumentKey`, `ArtifactKey`, `IdentityManifest` |
| relationship | typed relation and exactly one artifact or URI target | `ArtifactRelationship` |
| diagnostics/location | stable code/severity/message/context and transport coordinates | `Diagnostic`, `SourceLocation` |
| presentation-only | source headings/frontmatter/sections and renderer projection | source-profile boundary; never canonicalized implicitly |
| consumer extension | recursively JSON-compatible value behind reverse-domain key | `ArtifactBase.extensions` |

Authorial lists preserve input order. Relationships, dependency/verification keys,
identity document keys, extension keys, and JSON object keys are set-like or maps
and serialize deterministically. Optional `None` fields are omitted; required
lists/maps and defaults are emitted.

## Runtime-only constraints

JSON Schema covers record shape, discriminators, patterns, cardinality, and the
measurement comparator target shape. Because JSON Schema classifies integral JSON
numbers such as `1.0` as integers, its float-range branch accepts only values that
are observably non-integral; Pydantic preserves and validates the Python numeric
type precisely. Pydantic/API validation additionally covers
artifact-prefix agreement, duplicate composite keys, reference existence,
identity registration conflicts, exact Python scalar type/finiteness/order for
measurements, provenance transitions, and source-root/symlink containment.

`ProfileDescriptor` is data only in A1. Source-profile discovery, precedence,
descriptor/module I/O, trust and hash verification, loading, invocation wrappers,
and operational profile error handling belong exclusively to A4.

## Stable operational codes

- `RAPTOR.PATH.OUTSIDE_ROOT`
- `RAPTOR.REFERENCE.UNRESOLVED`, `.DUPLICATE`, `.RESOLVER_REQUIRED`
- `RAPTOR.IDENTITY.MISSING`, `.REPOSITORY_CONFLICT`, `.DOCUMENT_CONFLICT`,
  `.PATH_CONFLICT`, `.REUSE`

A4 owns acceptance and executable use of the reserved profile codes:
`RAPTOR.PROFILE.AMBIGUOUS`, `.VERSION`, `.API`, `.ENTRYPOINT`, `.HASH`,
`.UNTRUSTED`, `.PARSE`, `.RETURN_TYPE`, `.VALIDATION`, and `.CANONICALIZE`.
