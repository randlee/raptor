use raptor_schema::*;
use rusqlite::Connection;

#[test]
fn fixture_and_emissions_are_valid() {
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("../../../tests/fixtures/records.json")).unwrap();
    let requirements: Vec<Requirement> =
        serde_json::from_value(fixture["requirements"].clone()).unwrap();
    let decisions: Vec<Decision> = serde_json::from_value(fixture["decisions"].clone()).unwrap();
    assert_eq!(requirements.len() + decisions.len(), 4);
    Connection::open_in_memory()
        .unwrap()
        .execute_batch(&sql_ddl())
        .unwrap();
    assert_eq!(field_table("requirements").len(), 8);
    assert!(json_schema().get("requirements").is_some());
}

#[test]
fn inventory_reports_each_duplicate() {
    let id: Id = "REQ-FIX-0001".parse().unwrap();
    let lifecycle = Lifecycle {
        status: Status::Draft,
        version: "1.0.0".parse().unwrap(),
        created: "2026-01-01".parse().unwrap(),
        last_updated: "2026-01-01".parse().unwrap(),
        owner: "Example".into(),
    };
    let rows = vec![
        Requirement {
            identity: Identity {
                id: id.clone(),
                title: "A".into(),
            },
            lifecycle: lifecycle.clone(),
        },
        Requirement {
            identity: Identity {
                id,
                title: "B".into(),
            },
            lifecycle,
        },
    ];
    assert_eq!(check_inventory(&rows, &[]).len(), 2);
}
