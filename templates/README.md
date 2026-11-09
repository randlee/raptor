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

## Render, import and query

Install once from this repository: `pip install . markdown sc-compose`. This
builds the `raptor_schema` module (PyO3) that the import uses to validate
records.

From the repository the record belongs to, with Raptor checked out at
`$RAPTOR` and a `.raptor/` inventory that includes the new file:

```sh
sc-compose render --root "$RAPTOR" --file templates/req-new.md.j2 \
  --var-file req.json --strict --unknown-var-mode error \
  --output docs/requirements/REQ-ABC-0001.md
python "$RAPTOR/scripts/extract.py" --project-root . --output index.json
python "$RAPTOR/scripts/load_sqlite.py" index.json requirements.sqlite
python "$RAPTOR/scripts/raptor_query.py" get REQ-ABC-0001 --db requirements.sqlite
```

`extract.py` writes the import index and exits 0 when every record imports
with no diagnostics; otherwise it prints each diagnostic and exits 1.
`load_sqlite.py` loads the index into the Raptor SQLite database, and
`raptor_query.py get` returns the stored record as JSON.

## judge-jev

judge-jev judges records from the import index that `extract.py` writes:

```sh
jev_judge.py quality --req REQ-ABC-0001 --index index.json
```

`--nfr` and `--adr` select the other kinds.
