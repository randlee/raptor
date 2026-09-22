# SQLite v2 persistence mapping

SQLite is a projection of the `2.0.0` generic record, not an alternate model.
`documents` owns the document envelope: provenance, title, metadata, and ordered
`non_item_segments_json`. `artifacts` owns one row per
`(repository_id, document_id, artifact_id)` and indexes its type, title, status,
domain, source JSON, and verbatim Markdown content. Repeated local IDs in
different documents are therefore valid and unambiguous.

`relationships` is the only relationship table. It stores the source triple,
source-relative ordinal, emitted `relation_type`, raw target token and context,
plus a nullable resolved target triple. Resolution is populated only when the
target token identifies exactly one artifact in the same repository. The raw
token and context are always retained.

Forward queries select `relationships` by the source repository/document
triple. Reverse (`referenced_by`) queries select it by the three nullable target
columns. No reverse rows, typed relationship enum, URI table, migration path, or
family-derived relationship projection exists in v2.

`sqlite/0001_initial.sql` is a replacement schema: imports create a fresh v2
database from Markdown/JSON. It has no compatibility migration from v1.
