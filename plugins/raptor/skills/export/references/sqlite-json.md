# SQLite → JSON

Inspect the JSON columns held by one artifact with SQLite:

```sh
sqlite3 requirements.sqlite "SELECT id, document_metadata, source, content, subsections FROM artifacts WHERE id = 'REQ-EXAMPLE-0001';"
```
