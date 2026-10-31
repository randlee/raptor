use super::common::fixture;
use raptor_schema::{TableId, accept};
use serde_json::json;
use std::path::{Path, PathBuf};

#[test]
fn each_table_routes_decoded_rows_only_to_its_matching_accessor() {
    for table in TableId::ALL {
        let row = fixture()[table.name()][0].clone();
        let input = match table {
            TableId::Req => json!({"requirements": [row], "decisions": []}),
            TableId::Dec => json!({"requirements": [], "decisions": [row]}),
        };
        let accepted = accept(&input.to_string());
        let counts = (
            accepted.batch.requirements().count(),
            accepted.batch.decisions().count(),
        );
        assert_eq!(
            counts,
            match table {
                TableId::Req => (1, 0),
                TableId::Dec => (0, 1),
            }
        );
    }
}

#[test]
fn batch_construction_and_mutators_are_called_only_by_ingress() {
    fn files(path: &Path, out: &mut Vec<PathBuf>) {
        for entry in std::fs::read_dir(path).unwrap() {
            let path = entry.unwrap().path();
            if path.is_dir() {
                files(&path, out);
            } else if path.extension().is_some_and(|ext| ext == "rs") {
                out.push(path);
            }
        }
    }
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut paths = Vec::new();
    files(&root, &mut paths);
    for path in paths {
        // Unit tests exercise private ingress and insertion-guard seams.
        if path == root.join("accept.rs")
            || path == root.join("batch.rs")
            || path == root.join("accept/tests.rs")
            || path == root.join("batch/tests.rs")
        {
            continue;
        }
        let text = std::fs::read_to_string(&path).unwrap();
        for call in ["Batch::new(", ".add_requirement(", ".add_decision("] {
            assert!(!text.contains(call), "{} contains {call}", path.display());
        }
    }
}
