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

When a migration authority reports that the identity is already owned elsewhere,
pass `--registered-repository-id <owner>`; a differing owner fails with
`RAPTOR.IDENTITY.REUSE` before mutation.

The built-in `raptor` Markdown profile is always available. A consumer may keep
its own profile at `.raptor/profiles/<profile-id>/<version>/profile.json`, with an
entrypoint and SHA-256 for a declaration in that same version directory. The
declaration is strict JSON containing only `kind: raptor-markdown-profile`, its
profile ID, and version; executable consumer code is not loaded. External
profiles still require `--allow-profile-code`, API version `1`, and no symlink or
root escape. Raptor does not copy consumer profiles into the plugin.

Reference modes are explicit. Markdown defaults to `document`; JSON defaults to
`structural`. Use `batch` for a directory whose documents refer to one another,
or `store --database <relative-path>` to resolve targets already in SQLite.
Directory Markdown import defaults to `batch` and writes one canonical JSON file
per registered document ID. Empty directories and non-batch directory modes are
rejected.

The native Markdown profile recognizes `REQ`, `NFR`, `ADR`, `DES`, and `TST`
artifact headings. Design bodies use `Overview:`, a pipe-separated `Component:`
(`name | responsibility`), optional comma-separated `Dependencies:`, and
`Interface:` (`name | description | participants`).
Test-plan bodies use `Objective:`, `Scope:`, `Test Case:`
(`id | title | semicolon-separated steps | expected result`), `Verifies:`, and
`Exit Criteria:`. There is no embedded-canonical-JSON escape hatch.

JSON→Markdown, semantic round-trip, and all Dolt routes remain unsupported until
their owning phases. No template or Dolt implementation is included here.
