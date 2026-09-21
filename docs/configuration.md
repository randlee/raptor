# Raptor repository configuration

Raptor repository configuration is owned and versioned by Raptor. A consuming
repository stores committed configuration below `.raptor/`; consumer-specific
conventions must not be added to the Raptor schema, examples, or tests.

## Ingress configuration inventory

Version 1 ingress starts at the repository root and reads
`.raptor/raptor.toml`. The following table exhaustively defines the committed
configuration selected by that manifest. An ingress operation must not infer an
omitted file or scan an undeclared path.

| Artifact | Format and model | Fields | Ownership and role |
|---|---|---|---|
| `.raptor/raptor.toml` | TOML decoded as `RepositoryConfigManifest` | `schema_version`, `repository_id`, `files.scan`, `files.routing`, `files.identity` | Required entrypoint. Names the three ingress artifacts relative to `.raptor/`; no conventional fallback is allowed. |
| manifest-selected scan file (normally `sources.toml`) | TOML decoded as `RepositoryScanConfig` | `schema_version`; each `sources[]`: `name`, `root`, `include`, optional `exclude` | Required scan authorization. It determines the complete set of files ingress may read. |
| manifest-selected routing file (normally `routing.toml`) | TOML decoded as `RepositoryRoutingConfig` | `schema_version`; each `routes[]`: `source`, `profile.profile_id`, `profile.profile_version`, `artifact_types` | Required source classification. It selects an exact format profile and the artifact families permitted for every scan source. |
| manifest-selected identity file (normally `identity.json`) | JSON decoded as `IdentityManifest` | `identity_version`, `repository_id`; `documents` object keyed by document ID with `path` | Required durable identity state. Document IDs and paths are one-to-one within the repository and the repository ID must agree with the entrypoint. |

Profile and template assets are committed repository data but are not yet named
by `RepositoryConfigManifest`. The current runtime discovers a selected
`.raptor/profiles/<profile-id>/<version>/profile.json` containing `profile_id`,
`profile_version`, `api_version`, `entrypoint`, and `module_sha256`, then reads
the hash-pinned adjacent JSON declaration named by `entrypoint`. The merged
architecture and runtime disagree about whether this boundary supports an
executable source profile or only a declaration selecting the built-in Markdown
implementation. Corpus ingress must not rely on a non-built-in profile until an
owning plan resolves that contract and updates the architecture, runtime, and
tests together.

Rendering is the reverse boundary, not ingress. A selected external template
set is stored at `.raptor/template-sets/<name>/template-set.json` with exactly
`name`, `version`, `templates`, and `sha256`. `templates` maps every canonical
artifact family to one direct-child `.j2` entry template; `sha256` maps every
inventoried template to its digest. Selection of a template set and staging
destination is an explicit operation input until a versioned repository model
defines otherwise.

Database destinations, credentials, validate/apply mode, reference-resolution
mode, temporary or staging paths, template-set selection, and the migration
trust-policy path are explicit operation inputs. The trust policy is strict JSON
containing `policy_version`, `authority_id`, and non-empty `tools`; each tool
entry contains `role`, `tool_id`, exact `tool_version`, a complete versioned
no-follow bundle inventory/root/source and digest, relative
entrypoint, deterministic version command and expected output, optional
interpreter pair, exact normalized `argv`, working-directory role, closed
environment, and complete auxiliary workspace-input inventory/digest. These
values are not authorized corpus content and must not be inferred from unrelated
files or stored in the ingress artifacts above.

## Generated runtime state

Generated state is never source input and must be excluded from scans:

| Namespace | Owner and lifecycle |
|---|---|
| `.raptor/state/logs/` | Agent-run audit output; append-only during an invocation and removable after evidence retention requirements are met. |
| `.raptor/identity.lock` | Process lock for identity and render transactions; ephemeral and never committed. |
| `.raptor/transactions/` | Phase A non-migration transaction state only; Phase B migration must not place journals here. |
| `.raptor/state/migrations/<id>/validation/` | B6 ledger, immutable apply plan, tree/identity stages, and SQLite mutation set. Only the ledger may advance through B7/B8's typed states; validate/apply-intent certification never creates destination siblings. |
| `.raptor/state/migrations/<id>/evidence/` and `certification.json` | B7/B8 evidence bound to the sealed validation inventory; durable audit state. |
| `.raptor/state/migrations/<id>/apply/{journal.json,result.json,operation.lock}` | B9-only recovery state. The lock is ephemeral; journal/result are retained at verified terminal state. |
| `<destination>.raptor-<id>.stage` and `<destination>.raptor-<id>.backup` | B9-only, journal-indexed siblings for output and selected identity puts/deletes; cleaned only after verified complete or rollback, retained on conflict. |

The literal operation locator is `.raptor/state/migrations/<operation_id>/`.
Operation IDs cannot be reused: an existing root is resumable only for the same
operation-input digest, otherwise it is a conflict. A validate run never creates
`apply/` or destination siblings. Recovery accepts only an operation ID, resolves
that locator, and rejects symlinks, missing/mismatched journals, live-lock
collisions, and unindexed siblings. Completed and rolled-back runs remove
ephemeral lock/stage/backup state after verification but retain the canonical
ledger/evidence/certification/journal/result; conflicts retain observed state.

The current runtime still hardcodes `.raptor/identity.json` in identity and
transaction paths. Repository-root corpus ingress is not conformant until the
manifest-selected identity path is propagated through those call sites.

## Scan authorization

The manifest-selected scan file (conventionally `.raptor/sources.toml`) is the
authoritative allowlist of files that Raptor may inspect. The file decodes to
`RepositoryScanConfig` and must validate against
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

The manifest-selected routing file (conventionally `.raptor/routing.toml`)
binds every named scan source to the source profile and canonical artifact
families permitted for that source. It decodes to
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
