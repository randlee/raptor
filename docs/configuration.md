# Raptor repository configuration

Raptor repository configuration is owned and versioned by Raptor. A consuming
repository stores committed configuration below `.raptor/`; consumer-specific
conventions must not be added to the Raptor schema, examples, or tests.

## Ingress configuration inventory

Configured batch ingress starts at the repository root and reads
`.raptor/raptor.toml`. An operation must not infer an omitted configuration file
or scan an undeclared path.

| Artifact | Format and model | Role |
|---|---|---|
| `.raptor/raptor.toml` | TOML `RepositoryConfigManifest` | Required entrypoint naming scan, routing, and identity artifacts. |
| manifest-selected scan file | TOML `RepositoryScanConfig` | Authorizes the complete set of readable source paths. |
| manifest-selected routing file | TOML `RepositoryRoutingConfig` | Selects the source profile and permitted artifact families for each scan source. |
| manifest-selected identity file | JSON `IdentityManifest` | Supplies stable repository/document identity and the one-to-one document-path mapping. |

Profiles and templates are committed repository data selected by operation
inputs. Database destination, validate/apply mode, reference-resolution mode,
and output paths are also explicit operation inputs; none are inferred from an
undeclared repository file.

## Generated runtime state

Generated state is never source input and must be excluded from scans.

| Namespace | Lifecycle |
|---|---|
| `.raptor/state/logs/` | Invocation audit output; retained or removed by the operator's evidence policy. |
| `.raptor/identity.lock` | Ephemeral identity/render lock; never committed. |
| `.raptor/transactions/` | Existing render-transaction state; never source input. |
| path-scoped `*.raptor-*.stage` and `*.raptor-*.backup` | Existing render stages/backups; removed only after the render transaction completes or recovers. |

## Scan authorization

`.raptor/sources.toml` is the authoritative allowlist of files that Raptor may
inspect. The file decodes to `RepositoryScanConfig` and must validate against
`schema/json/v1/repository-scan-config.schema.json` before filesystem traversal.
The initial contract answers only which files may be inspected. Artifact-family,
parser, mapping, and rendering rules are separate future configuration contracts.

An absent configuration, an empty `sources` array, or an invalid configuration
authorizes no scanning. Raptor must never fall back to scanning the repository.

```toml
schema_version = "1.0.0"

[[sources]]
name = "product-requirements"
root = "specifications/requirements"
include = ["*.md", "**/*.md"]
exclude = ["README.md", "archive/**"]

[[sources]]
name = "architecture-decisions"
root = "architecture/decisions"
include = ["*.md", "**/*.md"]
exclude = ["README.md"]
```

### Field requirements

| Field | Required | Requirements |
|---|---:|---|
| `schema_version` | yes | Semantic version with supported major `1`. |
| `sources` | yes | Non-empty array of uniquely named, non-overlapping source declarations. |
| `sources[].name` | yes | Stable lowercase name matching `[a-z][a-z0-9_-]{0,63}`; unique within the file. |
| `sources[].root` | yes | Unique, normalized, repository-relative POSIX directory without an empty, `.` or `..` segment. Repository root itself is not valid. |
| `sources[].include` | yes | Non-empty set of unique globs evaluated relative to `root`. A file must match at least one. |
| `sources[].exclude` | no | Set of unique globs evaluated after inclusion. A match denies the file. Defaults to empty. |

Unknown fields are errors. Configuration values are not environment-expanded,
shell-expanded, URL-decoded, or interpreted as regular expressions.
JSON Schema enforces structural and per-value constraints, including identical
array-item duplication. Cross-source name uniqueness and ancestor/descendant root
overlap are runtime Pydantic checks because those comparisons are not generally
expressible in standard JSON Schema.

### Glob dialect

Paths and patterns use `/` on every operating system. Matching is case-sensitive
and applies to the complete path relative to the declared root:

- `*` matches zero or more characters except `/`.
- `?` matches exactly one character except `/`.
- `**` matches across directory boundaries.
- `**/` matches zero or more complete directory segments.
- bracket classes, brace expansion, backslash escaping, and leading `!` negation
  are unsupported and invalid.

Exclusion wins over inclusion. Declaration order has no effect. Source roots may
not be equal, ancestors, or descendants of one another. A repository needing
different rules below a parent directory must declare disjoint roots and adjust
the parent declaration rather than relying on precedence.

### Filesystem boundary

Before reading a matched path, an implementation must resolve the repository
root, source root, and candidate and verify containment. It must not follow a
symbolic link that escapes either the declared source root or repository root.
`.git/` and `.raptor/` are control directories and are never input candidates,
even if a future configuration declaration would otherwise match them.

The resulting inventory is de-duplicated and sorted by repository-relative POSIX
path before parsing. A file not matched by exactly one validated source
declaration is unauthorized and must not be read by a scan operation.

## Source routing

`.raptor/routing.toml` binds every named scan source to the source profile and
canonical artifact families permitted for that source. It decodes to
`RepositoryRoutingConfig` and validates against
`schema/json/v1/repository-routing-config.schema.json`.

```toml
schema_version = "1.0.0"

[[routes]]
source = "product-requirements"
artifact_types = ["requirement", "non_functional_requirement"]

[routes.profile]
profile_id = "raptor"
profile_version = "1.0.0"

[[routes]]
source = "architecture-decisions"
artifact_types = ["architecture_decision"]

[routes.profile]
profile_id = "raptor"
profile_version = "1.0.0"
```

### Routing field requirements

| Field | Required | Requirements |
|---|---:|---|
| `schema_version` | yes | Semantic version with supported major `1`. |
| `routes` | yes | Non-empty array; every source declared in `sources.toml` appears exactly once and no undeclared source appears. |
| `routes[].source` | yes | Exact stable name of one scan source. Routing never matches raw folder strings independently. |
| `routes[].profile.profile_id` | yes | Lowercase Raptor source-profile identifier. |
| `routes[].profile.profile_version` | yes | Exact three-component numeric semantic version; leading zeroes, prerelease/build suffixes, ranges, and floating labels are invalid. |
| `routes[].artifact_types` | yes | Non-empty unique allowlist drawn from `requirement`, `non_functional_requirement`, `architecture_decision`, `design_document`, and `test_plan`. |

JSON Schema enforces structural constraints and identical route duplication.
Duplicate source names with otherwise different route values, and cross-file
source coverage, are runtime Pydantic comparisons.

The scan and routing files are validated together before reading source content.
Missing routes, unknown sources, duplicate routes, unavailable profiles, and
artifacts outside a route's family allowlist are hard errors. Declaration order
does not define precedence. Resolved routes follow scan-source declaration order
to keep processing deterministic.

Routing selects a declared profile; it does not define executable entrypoints or
trust policy. Profile installation and availability are runtime responsibilities.
Repository-specific Markdown conventions remain in the selected profile rather
than becoming Raptor canonical fields.

## Repository manifest

`.raptor/raptor.toml` is the required configuration entrypoint. It establishes
the repository identity and explicitly names the scan, routing, and identity
artifacts relative to `.raptor/`.

```toml
schema_version = "1.0.0"
repository_id = "urn:raptor:repo:raptor"

[files]
scan = "sources.toml"
routing = "routing.toml"
identity = "identity.json"
```

| Field | Required | Requirements |
|---|---:|---|
| `schema_version` | yes | Supported Raptor configuration schema version. |
| `repository_id` | yes | Stable Raptor repository URN; it must equal the identity manifest repository ID. |
| `files.scan` | yes | Unique `.toml` path relative to `.raptor/`; no default is inferred. |
| `files.routing` | yes | Unique `.toml` path relative to `.raptor/`; no default is inferred. |
| `files.identity` | yes | Unique `.json` path relative to `.raptor/`; no default is inferred. |

Artifact paths use normalized POSIX syntax and cannot be absolute, traverse with
`.` or `..`, contain backslashes, or redundantly include `.raptor/`. Missing or
invalid referenced files make the repository configuration invalid; implementations
must not substitute conventional filenames or scan the repository implicitly.
Path distinctness and repository-ID agreement are cross-field/cross-file runtime
checks; JSON Schema enforces each individual path's syntax and required file type.
