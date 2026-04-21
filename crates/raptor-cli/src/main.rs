use anyhow::Result;
use clap::Parser;

#[derive(Parser)]
#[command(
    name = "raptor",
    version,
    about = "Requirements, architecture, plan, test, observability and reporting system for AI agent access"
)]
struct Cli {}

fn main() -> Result<()> {
    let _cli = Cli::parse();
    Ok(())
}
