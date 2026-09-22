---
name: import-corpus
description: Extract a repository's Markdown artifacts into a JSON index, correct diagnostics, and load SQLite.
---

# Import a documentation corpus

Run the commands from the target repository, not from Raptor:

```sh
python /path/to/raptor/scripts/extract.py . --output .raptor/requirements-index.json
```

The extractor writes a diagnostic for each unreadable Markdown file. Treat every
diagnostic as a source-document problem, correct the Markdown, then run the
command again. Do not import until it reports `diagnostics=0`.

Once clean, load the index into a development SQLite database:

```sh
python /path/to/raptor/scripts/load_sqlite.py \
  .raptor/requirements-index.json .raptor/requirements.sqlite
```

The load is idempotent: each run replaces the database's artifact and
relationship rows with the index contents. To reconstruct Markdown for review,
use `render.py` against the same index and the Raptor `templates/` directory.
