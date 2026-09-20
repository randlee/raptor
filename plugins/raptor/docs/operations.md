# Raptor plugin operations

Sprint A4 activates six routes: Markdown→JSON, JSON→SQLite, SQLite→JSON, and
validation for each of those three representations. Every command validates by
default; pass `--apply` to authorize its single file or database mutation.

Markdown repositories register durable identities in `.raptor/identity.json`:

```sh
python plugins/raptor/scripts/identity.py register \
  --repo-root . --repository-id urn:raptor:repo:example \
  --document-id DOC-RAP-001 --path docs/requirements.md --apply
```

The built-in `raptor` Markdown profile is always available. A consumer may keep
its own profile at `.raptor/profiles/<profile-id>/<version>/profile.json`, with an
entrypoint and SHA-256 for a module in that same version directory. External
profile code runs only with `--allow-profile-code`; it must use API version `1`,
cannot use a symlink or escape its profile root, and must not import network
clients. Raptor does not copy consumer profiles into the plugin.

Reference modes are explicit. Markdown defaults to `document`; JSON defaults to
`structural`. Use `batch` for a directory whose documents refer to one another,
or `store --database <relative-path>` to resolve targets already in SQLite.

JSON→Markdown, semantic round-trip, and all Dolt routes remain unsupported until
their owning phases. No template or Dolt implementation is included here.
