# Raptor repository configuration

Raptor repository configuration is owned and versioned by Raptor. A consuming
repository stores committed configuration below `.raptor/`; consumer-specific
conventions must not be added to the Raptor schema, examples, or tests.

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
