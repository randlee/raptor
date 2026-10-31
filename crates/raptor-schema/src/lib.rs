mod accept;
mod batch;
mod boundary;
mod emit;
mod error;
mod fields;
mod inventory;
mod metadata;
mod protocol;
mod rule;
mod schema;
pub use accept::{Accepted, accept};
pub use batch::Batch;
pub use emit::{FieldMeta, MetaLevel, MetaShape, Role, field_table, json_schema, sql_ddl};
pub use error::{Error, ErrorCategory, ItemIndex, RecordPosition, TableId};
pub use inventory::Summary;
pub use metadata::FieldScope;
pub use rule::Rule;
pub use schema::{
    Alternative, Alternatives, CheckItem, Consequences, Context, Date, Decision, DecisionRationale,
    DecisionSection, Dependencies, Id, IdItem, Identity, ImpactAnalysis, Implementation,
    ImplementationNotes, Lifecycle, LinkItem, Modal, ProductApplicability, RecordKind,
    RelatedDocuments, Requirement, RequirementStatement, Statement, Status, SuccessCriteria,
    TestStrategy, Version, validate_scalar,
};

#[cfg(feature = "python")]
mod python {
    use super::{Error, ErrorCategory, emit, schema};
    use pyo3::{exceptions::PyValueError, prelude::*, types::PyDict};
    pyo3::create_exception!(raptor_schema, SchemaError, PyValueError);

    fn json(py: Python<'_>, value: impl serde::Serialize) -> PyResult<String> {
        match serde_json::to_string(&value) {
            Ok(output) => Ok(output),
            Err(error) => fail(py, Error::serialization("a serializable result", error)),
        }
    }
    fn fail<T>(py: Python<'_>, error: Error) -> PyResult<T> {
        let exception = SchemaError::new_err(error.to_string());
        let fields = py
            .import("json")?
            .call_method1(
                "loads",
                (serde_json::to_string(&error)
                    .map_err(|failure| PyValueError::new_err(failure.to_string()))?,),
            )?
            .downcast_into::<PyDict>()?;
        for (name, value) in fields.iter() {
            exception
                .value(py)
                .setattr(name.extract::<String>()?, value)?;
        }
        Err(exception)
    }
    #[pyfunction]
    fn sql_ddl() -> String {
        emit::sql_ddl()
    }
    #[pyfunction]
    fn json_schema(py: Python<'_>) -> PyResult<String> {
        json(py, emit::json_schema())
    }
    #[pyfunction]
    fn field_table(py: Python<'_>, table: &str) -> PyResult<String> {
        match super::TableId::ALL.iter().find(|kind| kind.name() == table) {
            Some(kind) => json(py, emit::field_table(*kind)),
            None => fail(
                py,
                Error::scalar(
                    ErrorCategory::UnknownVariant,
                    table,
                    "one of requirements or decisions",
                ),
            ),
        }
    }
    #[pyfunction]
    fn validate_scalar(py: Python<'_>, kind: &str, text: &str) -> PyResult<()> {
        match schema::validate_scalar(kind, text) {
            Ok(()) => Ok(()),
            Err(error) => fail(py, error),
        }
    }
    #[pyfunction]
    fn accept(py: Python<'_>, input: &str) -> PyResult<String> {
        json(py, crate::accept(input))
    }
    #[pymodule]
    fn raptor_schema(module: &Bound<'_, PyModule>) -> PyResult<()> {
        module.add("SchemaError", module.py().get_type::<SchemaError>())?;
        module.add_function(wrap_pyfunction!(sql_ddl, module)?)?;
        module.add_function(wrap_pyfunction!(json_schema, module)?)?;
        module.add_function(wrap_pyfunction!(field_table, module)?)?;
        module.add_function(wrap_pyfunction!(validate_scalar, module)?)?;
        module.add_function(wrap_pyfunction!(accept, module)?)
    }
}
