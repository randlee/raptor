import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "ci_scope", Path(__file__).parents[1] / ".github" / "scripts" / "ci_scope.py"
)
ci_scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ci_scope)


def test_runtime_paths() -> None:
    for path in (
        "crates/raptor-core/src/lib.rs",
        "Cargo.toml",
        "Cargo.lock",
        "rust-toolchain.toml",
        "scripts/extract.py",
        "tests/fixtures/items.md",
        "schema/example.sql",
        "templates/adr.md.j2",
        ".raptor/sources.toml",
        ".github/workflows/ci.yml",
        ".github/scripts/ci_scope.py",
        "tools/anything.py",
        "pyproject.toml",
        "requirements-dev.txt",
    ):
        assert ci_scope.requires_runtime([path]), path


def test_documentation_only_paths() -> None:
    paths = [
        "README.md",
        "AGENTS.md",
        "docs/project-plan.md",
        "docs/adr/0001.md",
        ".claude/skills/x/SKILL.md",
        "plugins/raptor/agents/json-validate.md",
        "",
    ]
    assert not ci_scope.requires_runtime(paths)
    assert ci_scope.requires_runtime([*paths, "crates/raptor-cli/src/main.rs"])
