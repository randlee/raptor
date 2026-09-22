# Repository configuration

Repository configuration lives in `.raptor/`. When it is present,
`scripts/extract.py` reads it unless repository-root or domain arguments are
provided. Configuration makes the permitted scan inventory explicit; it is not
generated runtime state.

| File | Purpose |
|---|---|
| `raptor.toml` | Names the scan, routing, and identity files. |
| `sources.toml` | Declares source roots and their include/exclude globs. |
| `routing.toml` | Declares allowed artifact types for each source. |
| `identity.json` | Stores the repository identifier and optional document map. |

`raptor.toml` requires `schema_version` and `repository_id`. The extractor
accepts and ignores both values. Its `[files]` table names `scan`, `routing`,
and `identity` artifacts relative to `.raptor/`.

`sources.toml` accepts `schema_version` and contains `[[sources]]` entries with a unique `name`, a
repository-relative `root`, non-empty `include` globs, and optional `exclude`
globs. The extractor reads only Markdown files selected by an include glob and
not selected by an exclude glob. Repeated glob matches are de-duplicated; paths
under `.git/` and `.raptor/` are never read.

`routing.toml` accepts `schema_version` and contains one `[[routes]]` entry for
every source. Each route sets `source` to that source name and provides an
`artifact_types` allowlist. The optional `[routes.profile]` table is accepted
and ignored.

| Route artifact type | Extractor behavior |
|---|---|
| `requirement` | Emits `REQ` records. |
| `non_functional_requirement` | Emits `NFR` records. |
| `architecture_decision` | Emits `ADR` records. |
| `test_plan` | Enables existing test-plan discovery. |
| `design_document` | Is accepted and currently emits no records. |

Any other artifact type is an error naming the routing file and value.

`identity.json` contains `identity_version`, `repository_id`, and a
`documents` map from stable document identifiers to repository-relative paths.
It establishes identity only; extraction does not create or update it.

The configuration has no locks, transactions, profile versions, or runtime
directories. Output paths remain explicit command-line arguments.
