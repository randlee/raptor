CREATE TABLE IF NOT EXISTS schema_metadata (
  metadata_key TEXT PRIMARY KEY,
  metadata_value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repositories (
  repository_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS documents (
  repository_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  current_path TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  title TEXT,
  metadata_json TEXT NOT NULL CHECK (json_valid(metadata_json)),
  non_item_segments_json TEXT NOT NULL CHECK (json_valid(non_item_segments_json)),
  origin_json TEXT NOT NULL CHECK (json_valid(origin_json)),
  materialization_json TEXT NOT NULL CHECK (json_valid(materialization_json)),
  canonical_sha256 TEXT NOT NULL CHECK (length(canonical_sha256) = 64),
  PRIMARY KEY (repository_id, document_id),
  UNIQUE (repository_id, current_path),
  FOREIGN KEY (repository_id) REFERENCES repositories(repository_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS artifacts (
  repository_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  artifact_type TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT,
  domain TEXT,
  source_json TEXT NOT NULL CHECK (json_valid(source_json)),
  content_markdown TEXT NOT NULL,
  artifact_json TEXT NOT NULL CHECK (json_valid(artifact_json)),
  PRIMARY KEY (repository_id, document_id, artifact_id),
  UNIQUE (repository_id, document_id, ordinal),
  FOREIGN KEY (repository_id, document_id) REFERENCES documents(repository_id, document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS relationships (
  source_repository_id TEXT NOT NULL,
  source_document_id TEXT NOT NULL,
  source_artifact_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  relation_type TEXT NOT NULL,
  target_token TEXT NOT NULL,
  context TEXT NOT NULL,
  target_repository_id TEXT,
  target_document_id TEXT,
  target_artifact_id TEXT,
  PRIMARY KEY (source_repository_id, source_document_id, source_artifact_id, ordinal),
  FOREIGN KEY (source_repository_id, source_document_id, source_artifact_id)
    REFERENCES artifacts(repository_id, document_id, artifact_id) ON DELETE CASCADE,
  FOREIGN KEY (target_repository_id, target_document_id, target_artifact_id)
    REFERENCES artifacts(repository_id, document_id, artifact_id) ON DELETE RESTRICT,
  CHECK ((target_repository_id IS NULL AND target_document_id IS NULL AND target_artifact_id IS NULL)
      OR (target_repository_id IS NOT NULL AND target_document_id IS NOT NULL AND target_artifact_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS relationships_target_idx
  ON relationships(target_repository_id, target_document_id, target_artifact_id);

INSERT OR IGNORE INTO schema_metadata(metadata_key, metadata_value)
VALUES ('database_schema_version', '2');
INSERT OR IGNORE INTO schema_metadata(metadata_key, metadata_value)
VALUES ('canonical_model_schema_version', '2.0.0');
