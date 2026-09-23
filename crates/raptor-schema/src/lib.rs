mod accept;
mod emit;
mod inventory;
mod schema;
pub use accept::{Accepted, Batch, Error, ErrorCategory, Recovery, accept};
pub use emit::{FieldMeta, field_table, json_schema, sql_ddl};
pub use inventory::{Rule, Summary};
pub use schema::*;

#[cfg(feature = "python")]
mod python {
    use super::{Error, ErrorCategory, emit, schema};
    use pyo3::{exceptions::PyValueError, prelude::*, types::PyDict};
    pyo3::create_exception!(raptor_schema, SchemaError, PyValueError);

    fn json(value: impl serde::Serialize) -> PyResult<String> {
        serde_json::to_string(&value).map_err(|error| PyValueError::new_err(error.to_string()))
    }
    fn fail<T>(py: Python<'_>, error: Error) -> PyResult<T> {
        let exception = SchemaError::new_err(error.to_string());
        let fields = py
            .import("json")?
            .call_method1("loads", (json(&error)?,))?
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
    fn json_schema() -> PyResult<String> {
        json(emit::json_schema().map_err(|error| PyValueError::new_err(error.to_string()))?)
    }
    #[pyfunction]
    fn field_table(py: Python<'_>, table: &str) -> PyResult<String> {
        match emit::TABLES.iter().find(|(name, _)| *name == table) {
            Some((_, kind)) => json(emit::field_table(*kind)),
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
    fn accept(input: &str) -> PyResult<String> {
        json(crate::accept(input))
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
