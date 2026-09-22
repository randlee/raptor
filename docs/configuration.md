# Repository configuration

Optional repository configuration lives in `.raptor/`. When it is present,
`scripts/extract.py` reads it unless a repository root or domain argument is
provided. Configuration makes the permitted scan inventory explicit; it is not
generated runtime state.

| File | Purpose |
|---|---|
| `raptor.toml` | `[files]` names the sources, routing, and identity files. |
| `sources.toml` | Declares source roots and their include/exclude globs. |
| `routing.toml` | Declares allowed artifact types for each source. |
| `identity.json` | Stores the repository identifier and optional document map. |

`sources.toml` contains `[[sources]]` entries with a unique `name`, a
repository-relative `root`, non-empty `include` globs, and optional `exclude`
globs. The extractor reads only Markdown files selected by an include glob and
not selected by an exclude glob. Repeated glob matches are de-duplicated.

`routing.toml` contains one `[[routes]]` entry for every source. Each route
sets `source` to that source name and provides an `artifact_types` allowlist.
The current extractor recognizes `REQ`, `NFR`, and `ADR`; records outside a
source's allowlist are not emitted.

`identity.json` contains `identity_version`, `repository_id`, and a
`documents` map from stable document identifiers to repository-relative paths.
It establishes identity only; extraction does not create or update it.

The configuration has no locks, transactions, profile versions, or runtime
directories. Output paths remain explicit command-line arguments.
