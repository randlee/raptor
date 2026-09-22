CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT NOT NULL, title TEXT NOT NULL, type TEXT NOT NULL, status TEXT,
    domain TEXT, document_metadata TEXT NOT NULL, source TEXT NOT NULL,
    content TEXT NOT NULL, subsections TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS relationships (
    source_id TEXT NOT NULL, relation_kind TEXT NOT NULL, target_id TEXT NOT NULL,
    context TEXT
);
CREATE INDEX IF NOT EXISTS relationships_target_idx ON relationships(target_id);
