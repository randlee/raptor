use thiserror::Error;

#[derive(Debug, Error)]
pub enum RaptorError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}
