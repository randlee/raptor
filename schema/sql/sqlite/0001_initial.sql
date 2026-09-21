CREATE TABLE IF NOT EXISTS schema_metadata (
  metadata_key TEXT PRIMARY KEY,
  metadata_value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repositories (
  repository_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS source_documents (
  repository_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  current_path TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  artifact_count INTEGER NOT NULL CHECK (artifact_count > 0),
  membership_sha256 TEXT NOT NULL CHECK (length(membership_sha256) = 64),
  canonical_sha256 TEXT NOT NULL CHECK (length(canonical_sha256) = 64),
  origin_json TEXT NOT NULL CHECK (json_valid(origin_json)),
  materialization_json TEXT NOT NULL CHECK (json_valid(materialization_json)),
  PRIMARY KEY (repository_id, document_id),
  UNIQUE (repository_id, current_path),
  FOREIGN KEY (repository_id) REFERENCES repositories(repository_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS artifacts (
  repository_id TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  status TEXT NOT NULL,
  artifact_json TEXT NOT NULL CHECK (json_valid(artifact_json)),
  PRIMARY KEY (repository_id, artifact_id),
  FOREIGN KEY (repository_id) REFERENCES repositories(repository_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS document_artifacts (
  repository_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  PRIMARY KEY (repository_id, document_id, artifact_id),
  UNIQUE (repository_id, artifact_id),
  UNIQUE (repository_id, document_id, ordinal),
  FOREIGN KEY (repository_id, document_id)
    REFERENCES source_documents(repository_id, document_id) ON DELETE CASCADE,
  FOREIGN KEY (repository_id, artifact_id)
    REFERENCES artifacts(repository_id, artifact_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS artifact_relationships (
  source_repository_id TEXT NOT NULL,
  source_artifact_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  target_repository_id TEXT NOT NULL,
  target_artifact_id TEXT NOT NULL,
  description TEXT,
  PRIMARY KEY (
    source_repository_id, source_artifact_id, relation,
    target_repository_id, target_artifact_id
  ),
  FOREIGN KEY (source_repository_id, source_artifact_id)
    REFERENCES artifacts(repository_id, artifact_id) ON DELETE CASCADE,
  FOREIGN KEY (target_repository_id, target_artifact_id)
    REFERENCES artifacts(repository_id, artifact_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS artifact_uri_relationships (
  source_repository_id TEXT NOT NULL,
  source_artifact_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  target_uri TEXT NOT NULL,
  description TEXT,
  PRIMARY KEY (source_repository_id, source_artifact_id, relation, target_uri),
  FOREIGN KEY (source_repository_id, source_artifact_id)
    REFERENCES artifacts(repository_id, artifact_id) ON DELETE CASCADE
);

INSERT OR IGNORE INTO schema_metadata(metadata_key, metadata_value)
VALUES ('database_schema_version', '1');

INSERT OR IGNORE INTO schema_metadata(metadata_key, metadata_value)
VALUES ('canonical_model_schema_version', '1.0.0');
