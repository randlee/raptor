"""Execute the repository's own configured inventory as an acceptance check."""

import json

from corpus_support import ROOT, run


def test_own_inventory_is_clean(tmp_path):
    destination = tmp_path / "inventory.json"
    result = run("extract.py", "--project-root", str(ROOT), "--output", str(destination))
    payload = json.loads(destination.read_text())
    assert result.returncode == 0
    assert payload["diagnostics"]["issues"] == []
    assert payload["metadata"]["records"] == 15


def test_default_output_argument_is_usable(tmp_path):
    result = run("extract.py", "--project-root", str(ROOT), cwd=tmp_path)
    destination = tmp_path / "requirements-index.json"
    assert destination.exists()
    assert json.loads(result.stdout)["index"] == "requirements-index.json"
