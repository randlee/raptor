"""Outside-repository smoke test for packaged SQLite DDL."""

from raptor_schema import SQLiteArtifactStore


store = SQLiteArtifactStore()
store.initialize()
assert store.list_artifact_keys() == []
store.close()
