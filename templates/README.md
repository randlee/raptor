# Record templates

These [sc-compose](https://github.com/randlee/sc-compose) templates write new
REQ, NFR and ADR records as Markdown. A record written from one imports into
the Raptor database with no diagnostics, and judge-jev reads it from the
import index.

| Template | Writes |
|---|---|
| `req-new.md.j2` | one REQ record |
| `nfr-new.md.j2` | one NFR record |
| `adr-new.md.j2` | one ADR record |
| `record.md.j2` | re-renders records already in an index (`scripts/render.py`) |

The three `*-new` templates are generated from the schema in
`crates/raptor-schema` by `python scripts/authoring_templates.py`. Do not
edit them by hand; a test fails when they differ from the schema.

## Variables

Variable names are the record's field names; each template's frontmatter
lists them with their defaults, and `tests/fixtures/authoring/` has one
sample vars file per kind.

- Required: `id`, `title`, `status`, `version`, `created`, `last_updated`,
  `owner`, plus `decision_date` for an ADR.
- List variables take one string per item. `must`, `should` and `must_not`
  hold one statement each. The reason goes in `rationale`, and project terms
  and acronyms go in `definitions`.
- A reference is `REQ-ABC-0002` or `REQ-ABC-0002 — note`. A link is
  `[text](url)`.
- An ADR's `alternatives` is a list of objects with `name`, `description`,
  `pros`, `cons` and `why_rejected`.
- Required sections always render, so an empty one is reported at import.
  Empty optional sections are left out.

## Render and import

Today the entrypoints are the Python scripts in `scripts/` and the
`raptor_schema` Python module (PyO3), which they call to validate records
(`accept`, `validate_scalar`, `json_schema`, `field_table`, `sql_ddl`,
`modal_mismatch`). The `raptor` CLI in `crates/raptor-cli` has no commands
yet. Install with `pip install . markdown sc-compose` from this repository.

From the repository the record belongs to, with Raptor checked out at
`$RAPTOR` and a `.raptor/` inventory that includes the new file:

```sh
sc-compose render --root "$RAPTOR" --file templates/req-new.md.j2 \
  --var-file req.json --strict --unknown-var-mode error \
  --output docs/requirements/REQ-ABC-0001.md
python "$RAPTOR/scripts/extract.py" --project-root . --output index.json
```

`extract.py` writes the import index and exits nonzero, printing each
diagnostic, when a record does not import cleanly. To load the database and
read records back:

```sh
python "$RAPTOR/scripts/load_sqlite.py" index.json requirements.sqlite
python "$RAPTOR/scripts/raptor_query.py" get REQ-ABC-0001 --db requirements.sqlite
```

## judge-jev

judge-jev reads records from the import index, not from SQLite:

```sh
jev_judge.py quality --req REQ-ABC-0001 --index index.json
```

`--nfr` and `--adr` select the other kinds.
