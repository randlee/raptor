---
name: query
description: Query an imported Raptor SQLite database with sqlite3.
---

# Raptor Query

Run these commands from the directory containing `requirements.sqlite`.

All requirements in a domain:

```sh
sqlite3 requirements.sqlite "SELECT id, title FROM artifacts WHERE domain = 'example';"
```

Everything that references an identifier:

```sh
sqlite3 requirements.sqlite "SELECT source_id, relation_kind FROM relationships WHERE target_id = 'REQ-EXAMPLE-0001';"
```

Everything with a status:

```sh
sqlite3 requirements.sqlite "SELECT id, title FROM artifacts WHERE status = 'Approved';"
```

The Markdown body of one identifier:

```sh
sqlite3 requirements.sqlite "SELECT json_extract(content, '$.markdown') FROM artifacts WHERE id = 'REQ-EXAMPLE-0001';"
```
